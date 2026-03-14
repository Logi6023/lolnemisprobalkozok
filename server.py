import asyncio
import json
import os
import websockets
from websockets.exceptions import ConnectionClosedError

PORT = int(os.getenv("PORT", 8080))

# connected_clients: { websocket: {"username": "bajtay"} }
connected_clients = {}


async def send_user_list():
    users = [data["username"] for data in connected_clients.values()]
    msg = json.dumps({
        "type": "user_list",
        "users": users
    })
    await asyncio.gather(*[
        ws.send(msg)
        for ws in connected_clients.keys()
    ], return_exceptions=True)


async def broadcast_message(sender_ws, text):
    sender_name = connected_clients.get(sender_ws, {}).get("username", "ismeretlen")

    msg = json.dumps({
        "type": "message",
        "from": sender_name,
        "text": text
    })

    await asyncio.gather(*[
        ws.send(msg)
        for ws in connected_clients.keys()
    ], return_exceptions=True)


async def handler(ws):
    print("[inf] Új kapcsolat érkezett")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print("[err] Rossz JSON:", raw)
                continue

            action = data.get("action")
            payload = data.get("data", {})

            # LOGIN
            if action == "login":
                username = payload.get("username")
                password = payload.get("password")

                # Itt lehetne valódi auth, most bárkit beengedünk
                if not username or not password:
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "Hiányzó felhasználónév vagy jelszó."
                    }))
                    continue

                connected_clients[ws] = {"username": username}
                print(f"[inf] Bejelentkezett: {username}")

                await ws.send(json.dumps({
                    "type": "login_ok",
                    "username": username
                }))

                await send_user_list()

            # SEND MESSAGE
            elif action == "send":
                text = payload.get("text", "").strip()
                if not text:
                    continue

                await broadcast_message(ws, text)

            else:
                print("[err] Ismeretlen action:", action)

    except ConnectionClosedError:
        # Normális, ha a kliens bezárja az ablakot / kilép
        print("[inf] A kliens bontotta a kapcsolatot (ConnectionClosedError).")

    except Exception as e:
        print("[err] Váratlan hiba a handlerben:", repr(e))

    finally:
        # Takarítás: ha volt login, töröljük a klienst
        if ws in connected_clients:
            user = connected_clients[ws]["username"]
            print(f"[inf] Kijelentkezett: {user}")
            del connected_clients[ws]
            await send_user_list()


async def main():
    print(f"[inf]  Szerver fut a porton: {PORT}")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # fut amíg meg nem állítják


if __name__ == "__main__":
    asyncio.run(main())
