"""
Gateway Demo
    1. 3 concurrent clients over different channels
    2. Reconnection with missed messages
    3. Rate limiting
    4. Invalid token rejection
    5. Logging verification
Run:
    1. uvicorn websocket.main:app --port 8000
    2. python websocket/demo.py
"""

import asyncio
import json
import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def get_token(user_id: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/auth/token", json={"user_id": user_id})
        return r.json()["token"]

async def connect(user_id: str, channel: str, session_id: str = None):
    token = await get_token(user_id)
    ws = await websockets.connect(WS_URL)
    handshake = {"token": token, "channel": channel}
    if session_id:
        handshake["session_id"] = session_id
    await ws.send(json.dumps(handshake))
    resp = json.loads(await ws.recv())
    return ws, resp.get("session_id")

# 3 Concurrent Clients 

async def single_client(name: str, user_id: str, channel: str, message: str):
    print(f"[{name}] Connecting on channel={channel}")
    ws, session_id = await connect(user_id, channel)
    print(f"[{name}] Connected — session_id={session_id}")
    await ws.send(json.dumps({"text": message}))
    response = json.loads(await ws.recv())
    print(f"[{name}] Response: {response.get('response')}")
    await ws.close()

async def scenario_concurrent_clients():
    print("\n" + "-"*50)
    print("3 Concurrent Clients")
    print("-"*50)
    await asyncio.gather(
        single_client("Web Client",   "user_alice", "web",   "Hi from web app!"),
        single_client("Slack Client", "user_bob",   "slack", "Hi from Slack"),
        single_client("X DM Client",  "user_carol", "x_dm",  "Hi from X DMs"),
    )
    print("[SCENARIO Concurrent Clients] Done\n")

# Reconnection

async def scenario_reconnection():
    print("\n" + "-"*50)
    print("Reconnection with Missed Messages")
    print("-"*50)

    ws, session_id = await connect("user_dave", "web")
    print(f"[RECONNECT] Connected — session_id={session_id}")
    await ws.close()
    print(f"[RECONNECT] Disconnected abruptly")

    await asyncio.sleep(1)

    print(f"[RECONNECT] Reconnecting with session_id={session_id}")
    ws, new_session_id = await connect("user_dave", "web", session_id=session_id)
    print(f"[RECONNECT] Reconnected — session_id={new_session_id}")

    try:
        missed = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
        print(f"[RECONNECT] Receive missed message: {missed}")
    except asyncio.TimeoutError:
        print(f"[RECONNECT] No missed messages recieved")

    await ws.close()
    print("[Reconnection] Done\n")

# Rate Limiting 

async def scenario_rate_limit():
    print("\n" + "-"*50)
    print("Rate Limiting (max 10 messages/min)")
    print("-"*50)

    ws, session_id = await connect("user_eve", "web")
    print(f"[RATE LIMIT] Connected — sending 12 messages rapidly")

    for i in range(12):
        await ws.send(json.dumps({"text": f"message {i+1}"}))
        resp = json.loads(await ws.recv())
        if resp.get("error") == "rate_limited":
            print(f"[RATE LIMIT] Rate limited on message {i+1} — working as expected")
            break
        else:
            print(f"[RATE LIMIT] Message {i+1} delivered")

    await ws.close()
    print("[Rate Limiting] Done\n")

# Invalid Token 

async def scenario_invalid_token():
    print("\n" + "-"*50)
    print("Invalid Token Rejection")
    print("-"*50)

    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({"token": "bad.token.here", "channel": "web"}))

    try:
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
        print(f"[AUTH] Server rejected invalid token: {resp}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[AUTH] Connection closed with code={e.code}")
    except asyncio.TimeoutError:
        print(f"[AUTH] Connection timed out (expected)")

    print("[Invalid Token] Done\n")

# Logging 

async def scenario_logging():
    print("\n" + "-"*50)
    print("Metrics")
    print("-"*50)
    print("[LOGGING] Fetching /metrics endpoint")

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/metrics")
        metrics = r.json()
        print(f"[LOGGING] Metrics snapshot:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

    print("[LOGGING] Check server terminal for structured JSON auth + message logs")
    print("[Metricx] Done\n")

# Main

async def main():
    print("\n" + "-"*50)
    print("Gateway Demo")
    print("-"*50)

    await scenario_concurrent_clients()
    await scenario_rate_limit()
    await scenario_invalid_token()
    await scenario_reconnection()
    await scenario_logging()

    print("-"*50)
    print("  All scenarios complete")
    print("-"*50)

if __name__ == "__main__":
    asyncio.run(main())