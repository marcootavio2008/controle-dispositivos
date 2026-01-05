from flask import Flask, render_template, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

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


@app.route('/')
def home():
    return render_template('controles.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
