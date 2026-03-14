import asyncio
import json
import os
import websockets

DATA_FILE = "data.json"
PORT = int(os.environ.get("PORT", 8000))

connected_users = {}  # websocket -> username


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "messages": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def register_user(ws, data_store, payload):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        await ws.send(json.dumps({"type": "error", "message": "Hiányzó username vagy password"}))
        return

    if username in data_store["users"]:
        await ws.send(json.dumps({"type": "error", "message": "Felhasználó már létezik"}))
        return

    data_store["users"][username] = {"password": password}
    save_data(data_store)
    await ws.send(json.dumps({"type": "info", "message": "Sikeres regisztráció"}))


async def login_user(ws, data_store, payload):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        await ws.send(json.dumps({"type": "error", "message": "Hiányzó username vagy password"}))
        return

    user = data_store["users"].get(username)
    if not user or user["password"] != password:
        await ws.send(json.dumps({"type": "error", "message": "Hibás belépési adatok"}))
        return

    connected_users[ws] = username
    await ws.send(json.dumps({"type": "info", "message": f"Bejelentkezve: {username}"}))


async def broadcast_message(sender_ws, data_store, payload):
    if sender_ws not in connected_users:
        await sender_ws.send(json.dumps({"type": "error", "message": "Nem vagy bejelentkezve"}))
        return

    username = connected_users[sender_ws]
    text = payload.get("text")
    if not text:
        await sender_ws.send(json.dumps({"type": "error", "message": "Üres üzenet"}))
        return

    msg = {"from": username, "text": text}
    data_store["messages"].append(msg)
    save_data(data_store)

    message_packet = json.dumps({"type": "message", "from": username, "text": text})
    for ws in list(connected_users.keys()):
        try:
            await ws.send(message_packet)
        except:
            pass


async def handler(ws, path):
    data_store = load_data()
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "message": "Érvénytelen JSON"}))
                continue

            action = msg.get("action")
            payload = msg.get("data", {})

            if action == "register":
                await register_user(ws, data_store, payload)
            elif action == "login":
                await login_user(ws, data_store, payload)
            elif action == "send":
                await broadcast_message(ws, data_store, payload)
            elif action == "history":
                await ws.send(json.dumps({"type": "history", "messages": data_store["messages"]}))
            else:
                await ws.send(json.dumps({"type": "error", "message": "Ismeretlen action"}))
    finally:
        if ws in connected_users:
            del connected_users[ws]


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Szerver fut a porton: {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
