from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
import os
import json

app = Flask(__name__)
sock = Sock(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===============================
# MODELOS
# ===============================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")
    
class House(db.Model):
    __tablename__ = "houses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.JSON, nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=False)

with app.app_context():
    db.create_all()


# ===============================
# CONTEXTO (QUERY STRING)
# ===============================

def get_context():
    user_id = request.args.get("user_id", type=int)
    house_id = request.args.get("house_id", type=int)

    if not user_id or not house_id:
        return None

    return user_id, house_id


# ===============================
# WEBSOCKET
# ===============================

connections = {}

@sock.route("/ws")
def ws_endpoint(ws):
    house_id = request.args.get("house_id", type=int)

    if not house_id:
        ws.close()
        return

    connections.setdefault(house_id, set()).add(ws)
    print(f"[WS] Client conectado | house_id={house_id}")

    try:
        while True:
            if ws.receive() is None:
                break
    finally:
        connections[house_id].discard(ws)
        if not connections[house_id]:
            del connections[house_id]

        print(f"[WS] Client desconectado | house_id={house_id}")


def enviar_comando_para_casa(house_id, comando):
    clients = connections.get(house_id)

    if not clients:
        print(f"[WS] Nenhum client conectado | house_id={house_id}")
        return False

    mortos = set()

    for ws in clients:
        try:
            ws.send(comando)
        except:
            mortos.add(ws)

    for ws in mortos:
        clients.discard(ws)

    print(f"[CMD] Enviado para house_id={house_id}")
    return True


# ===============================
# ROTAS
# ===============================

@app.route("/")
def home():
    user_id = request.args.get("user_id", type=int)
    house_id = request.args.get("house_id", type=int)

    if not house_id:
        return "house_id não informado", 400

    devices = Device.query.filter_by(house_id=house_id).all()
    return render_template("controles.html", devices=devices)



@app.route("/add_dispositivo")
def add_dispositivo():
    ctx = get_context()
    if not ctx:
        return "Contexto inválido", 400

    user_id, house_id = ctx
    return render_template(
        "add.html",
        user_id=user_id,
        house_id=house_id
    )


@app.route("/api/devices", methods=["POST"])
def save_device():
    ctx = get_context()
    if not ctx:
        return jsonify({"error": "contexto inválido"}), 400

    user_id, house_id = ctx
    data = request.json

    device = Device(
        name=data["name"],
        device_type=data["device_type"],
        config=data.get("config", {}),
        house_id=house_id,
        user_id=user_id
    )

    db.session.add(device)
    db.session.commit()

    return jsonify({"status": "ok"})


@app.route("/device/<int:device_id>/toggle", methods=["POST"])
def toggle_device(device_id):
    ctx = get_context()
    if not ctx:
        return jsonify({"error": "contexto inválido"}), 400

    _, house_id = ctx

    device = Device.query.get(device_id)

    if not device or device.house_id != house_id:
        return jsonify({"error": "dispositivo inválido"}), 404

    comando = json.dumps({
        "action": "toggle",
        "device_id": device.id,
        "type": device.device_type,
        "config": device.config
    })

    ok = enviar_comando_para_casa(house_id, comando)

    if not ok:
        return jsonify({"error": "Casa offline"}), 503

    return jsonify({"status": "ok"})


@app.route("/api/devices/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):
    ctx = get_context()
    if not ctx:
        return jsonify({"error": "contexto inválido"}), 400

    user_id, house_id = ctx

    device = Device.query.get(device_id)

    if not device or device.house_id != house_id:
        return jsonify({"error": "dispositivo inválido"}), 404

    if device.user_id != user_id:
        return jsonify({"error": "acesso negado"}), 403

    db.session.delete(device)
    db.session.commit()

    return jsonify({"status": "dispositivo removido"})


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
