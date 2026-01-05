from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy.dialects.postgresql import JSONB

app = Flask(__name__)
sock = Sock(app)


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)

    # futuramente: user_id
    name = db.Column(db.String(100), nullable=False)

    device_type = db.Column(db.String(30), nullable=False)  # lan | arduino | tuya
    trigger_type = db.Column(db.String(30), nullable=False)

    config = db.Column(JSONB, nullable=False)

with app.app_context():
    db.create_all()

# Lista de conexões WebSocket ativas
connections = []


@sock.route('/ws')
def ws_endpoint(ws):
    # Adiciona conexão ativa
    connections.append(ws)
    print("[WS] Cliente conectado")

    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break  # Conexão fechada
            print("[WS] Mensagem recebida:", msg)

    except Exception as e:
        print("[WS] Erro na conexão:", e)

    finally:
        if ws in connections:
            connections.remove(ws)
        print("[WS] Cliente desconectado")


def enviar_comando(comando):
    """Envia comando a todas as conexões ativas."""
    print(f"[CMD] Enviando comando: {comando}")
    removals = []
    
    for pc in connections:
        try:
            pc.send(comando)
        except:
            removals.append(pc)

    # Remove conexões com problema
    for pc in removals:
        if pc in connections:
            connections.remove(pc)
            print("[WS] Conexão removida por erro")


@app.route("/controle_luz")
def controle_luz():
    acao = request.args.get("acao")

    if acao == "ligar":
        enviar_comando("LIGAR_LUZ")
        return jsonify({"status": "luz ligada"})

    elif acao == "desligar":
        enviar_comando("DESLIGAR_LUZ")
        return jsonify({"status": "luz desligada"})

    return jsonify({"erro": "comando inválido"}), 400

@app.route('/add_dispositivo')
def add_dispositivo():
    return render_template('add.html')

@app.route('/api/devices', methods=['POST'])
def save_device():
    data = request.json

    device = Device(
        name=data["name"],
        device_type=data["device_type"],
        trigger_type=data["trigger"],
        config=data["config"]
    )

    db.session.add(device)
    db.session.commit()

    return jsonify({"status": "ok"})

@app.route('/')
def home():
    devices = Device.query.all()
    return render_template('controles.html', devices=devices)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
