from flask import Flask, render_template, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

# Lista de conexões WebSocket ativas
connections = []


@sock.route('/ws')
def ws_endpoint(ws):
    connections.append(ws)
    print("PC conectado via WebSocket")

    try:
        while True:
            msg = ws.receive()
            if msg:
                print("Mensagem recebida:", msg)

    except Exception as e:
        print("PC desconectado:", e)

    finally:
        if ws in connections:
            connections.remove(ws)
        print("Conexão removida.")


@app.route("/controle_luz")
def controle_luz():
    acao = request.args.get("acao")

    if acao == "ligar":
        print("Enviando comando LIGAR")
        for pc in connections:
            try:
                pc.send("LIGAR_LUZ")
            except:
                pass

        return jsonify({"status": "luz ligada"})

    elif acao == "desligar":
        print("Enviando comando DESLIGAR")
        for pc in connections:
            try:
                pc.send("DESLIGAR_LUZ")
            except:
                pass

        return jsonify({"status": "luz desligada"})

    return jsonify({"erro": "comando invalido"})


@app.route('/')
def home():
    return render_template('controles.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
