from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
import os
from flask import session
from sqlalchemy.dialects.postgresql import JSONB
import json

app = Flask(__name__)
sock = Sock(app)
app.secret_key = "controle123"

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

def get_current_user():
    if "user_id" not in session:
        return None

    return {
        "id": session["user_id"],
        "role": session.get("role", "user"),
        "house_id": session.get("house_id")
    }


connections = {}  # { house_id: set(ws) }

@sock.route("/ws")
def ws_endpoint(ws):
    house_id = request.args.get("house_id")

    if not house_id:
        ws.close()
        return

    house_id = int(house_id)

    connections.setdefault(house_id, set()).add(ws)

    print(f"[WS] Client conectado | house_id={house_id}")

    try:
        while True:
            msg = ws.receive()
            if msg is None:
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

    # limpa conexões mortas
    for ws in mortos:
        clients.discard(ws)

    print(f"[CMD] Enviado para house_id={house_id}")
    return True


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

@app.route("/api/houses")
def list_houses():
    user = get_current_user()
    if not user:
        return jsonify([])

    houses = House.query.filter_by(owner_id=user["id"]).all()

    return jsonify([
        {
            "id": h.id,
            "name": h.name
        } for h in houses
    ])


@app.route('/add_dispositivo')
def add_dispositivo():
    user = get_current_user()
    if not user:
        return "Usuário não identificado", 401

    return render_template("add.html", user=user)

@app.route("/api/devices", methods=["POST"])
def save_device():
    user = get_current_user()

    device = Device(
        name=data["name"],
        device_type=data["device_type"],
        config=data["config"],
        house_id=session["house_id"]
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

    if user["role"] != "admin" and device.user_id != user["id"]:
        return jsonify({"error": "acesso negado"}), 403

    comando = json.dumps({
        "action": "toggle",
        "device_id": device.id,
        "type": device.device_type,
        "config": device.config
    })

    ok = enviar_comando_para_casa(device.house_id, comando)

    if not ok:
        return jsonify({"error": "Casa offline"}), 503

    return jsonify({"status": "ok"})

@app.route("/api/devices/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "usuário não identificado"}), 401

    device = Device.query.get(device_id)
    if not device:
        return jsonify({"error": "dispositivo não encontrado"}), 404

    # 🔒 Permissão
    if user["role"] != "admin" and device.user_id != user["id"]:
        return jsonify({"error": "acesso negado"}), 403

    db.session.delete(device)
    db.session.commit()

    return jsonify({"status": "dispositivo removido"})

@app.route("/")
def home():
    user = get_current_user()

    if not user or not user["house_id"]:
        return "Casa não selecionada", 400

    devices = Device.query.filter_by(
        house_id=user["house_id"]
    ).all()

    return render_template(
        "controles.html",
        devices=devices
    )



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
