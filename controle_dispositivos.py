from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
import os
from flask import session
from sqlalchemy.dialects.postgresql import JSONB

app = Flask(__name__)
sock = Sock(app)
app.secret_key = "controle123"

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    device_type = db.Column(db.String(20), nullable=False)
    config = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()

def get_current_user():
    if "user_id" not in session:
        return None

    return {
        "id": session["user_id"],
        "role": session.get("role", "user")
    }

connections = {}  # { user_id: ws }

@sock.route('/ws')
def ws_endpoint(ws):
    user_id = request.args.get("user_id")

    if not user_id:
        ws.close()
        return

    user_id = int(user_id)
    connections[user_id] = ws

    print(f"[WS] PC conectado | user_id={user_id}")

    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break
            print(f"[WS] Msg de {user_id}: {msg}")

    except Exception as e:
        print("[WS] Erro:", e)

    finally:
        connections.pop(user_id, None)
        print(f"[WS] PC desconectado | user_id={user_id}")


def enviar_comando_para_usuario(user_id, comando):
    ws = connections.get(user_id)

    if not ws:
        print(f"[WS] Nenhum PC conectado para user {user_id}")
        return False

    try:
        ws.send(comando)
        print(f"[CMD] {comando} enviado para user {user_id}")
        return True

    except Exception as e:
        print("[WS] Erro ao enviar comando:", e)
        connections.pop(user_id, None)
        return False


@app.route("/controle_luz")
def controle_luz():
    user = get_current_user()
    if not user:
        return jsonify({"error": "não autenticado"}), 401

    acao = request.args.get("acao")

    if acao == "ligar":
        ok = enviar_comando_para_usuario(
            user["id"],
            "LIGAR_LUZ"
        )
        return jsonify({"status": ok})

    elif acao == "desligar":
        ok = enviar_comando_para_usuario(
            user["id"],
            "DESLIGAR_LUZ"
        )
        return jsonify({"status": ok})

    return jsonify({"error": "ação inválida"}), 400

@app.route('/add_dispositivo')
def add_dispositivo():
    user = get_current_user()
    if not user:
        return "Usuário não identificado", 401

    return render_template("add.html", user=user)


@app.route('/api/devices', methods=['POST'])
def save_device():
    user = get_current_user()
    if not user:
        return jsonify({"error": "usuário não identificado"}), 401

    data = request.json

    device = Device(
        name=data["name"],
        device_type=data["device_type"],
        config=data["config"],
        user_id=user["id"]
    )

    db.session.add(device)
    db.session.commit()

    return jsonify({"status": "ok"})

@app.route("/device/<int:device_id>/toggle", methods=["POST"])
def toggle_device(device_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "usuário não identificado"}), 401

    device = Device.query.get(device_id)

    if not device:
        return jsonify({"error": "dispositivo não encontrado"}), 404

    # 🔒 segurança: só dono ou admin
    if user["role"] != "admin" and device.user_id != user["id"]:
        return jsonify({"error": "acesso negado"}), 403

    # 🔌 comando enviado ao PC
    comando = {
        "action": "toggle",
        "device_id": device.id,
        "name": device.name,
        "type": device.device_type,
        "config": device.config
    }

    enviar_comando(json.dumps(comando))

    return jsonify({"status": "ok"})

@app.route('/')
def home():
    user_id = request.args.get("user_id")
    role = request.args.get("role", "user")

    if user_id:
        session["user_id"] = int(user_id)
        session["role"] = role

    if "user_id" not in session:
        return "Usuário não identificado", 401

    if session["role"] == "admin":
        devices = Device.query.all()
    else:
        devices = Device.query.filter_by(
            user_id=session["user_id"]
        ).all()

    return render_template(
        'controles.html',
        devices=devices,
        user={
            "id": session["user_id"],
            "role": session["role"]
        }
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
