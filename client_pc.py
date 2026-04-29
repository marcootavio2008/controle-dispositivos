import asyncio
import json
import time
import websockets

# ==========================
# CONFIG
# ==========================

SERVER_URL = "wss://controle-dispositivos.onrender.com/ws?house_id=1"
# SERVER_URL = "ws://127.0.0.1:8000/ws?house_id=1"

# ==========================
# AÇÕES DOS DISPOSITIVOS
# ==========================

def executar_comando(cmd):
    print("📩 Comando recebido:", cmd)

    device_id = cmd.get("device_id")
    state = cmd.get("state")
    dev_type = cmd.get("type")

    if dev_type == "lampada":
        if state:
            print(f"💡 LIGAR lâmpada {device_id}")
        else:
            print(f"💡 DESLIGAR lâmpada {device_id}")

    elif dev_type == "tomada":
        if state:
            print(f"🔌 LIGAR tomada {device_id}")
        else:
            print(f"🔌 DESLIGAR tomada {device_id}")

    else:
        print("⚠️ Tipo desconhecido:", dev_type)

# ==========================
# WEBSOCKET (ASYNC)
# ==========================

async def conectar():
    print("⏳ Tentando conectar...")

    async with websockets.connect(SERVER_URL) as ws:
        print("✅ Conectado à casa")

        while True:
            try:
                message = await ws.recv()
                cmd = json.loads(message)
                executar_comando(cmd)

            except json.JSONDecodeError:
                print("❌ JSON inválido:", message)

            except websockets.ConnectionClosed:
                print("🔌 Conexão encerrada")
                break

            except Exception as e:
                print("❌ Erro ao processar mensagem:", e)

# ==========================
# LOOP COM RECONEXÃO
# ==========================

async def start():
    while True:
        try:
            await conectar()

        except Exception as e:
            print("❌ Falha na conexão:", e)

        print("⏳ Reconectando em 5s...")
        await asyncio.sleep(5)

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    asyncio.run(start())