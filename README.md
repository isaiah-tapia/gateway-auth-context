# Gateway

Real-time WebSocket gateway with JWT authentication and multi-channel routing.

## Project Structure

```
gateway-auth/
├──endpoint/
│   ├── auth.py          # authenticate / create token
│   ├── session.py       # instaniate sessions
├── websocket/
│   ├── main.py          # FastAPI app, WebSocket endpoint
│   ├── session.py       # Session + SessionStore
│   ├── auth.py          # JWT create + verify
│   ├── metrics.py       # Metrics tracking
│   └── demo.py          # 5-scenario demo script
├── adapters/
│   ├── abstractAdapter.py
│   ├── webAdapter.py
│   ├── slackAdapter.py
│   └── xAdapter.py
└── requirements.txt
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
# Terminal 1 — start the server
uvicorn websocket.main:app --port 8000

# Terminal 2 — run the demo
python websocket/demo.py
```

## Scenarios

1. **concurrent clients** web, slack, and x_dm connect simultaneously
2. **Rate limiting** session is limited after 10 messages per minute
3. **Invalid token rejection** bad JWT is rejected at handshake
4. **Reconnection** client disconnects and resumes with same session_id
5. **Metrics** live snapshot of connections, messages, latency, auth failures

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/token` | POST | Issue a JWT given a user_id |
| `/ws` | WebSocket | Main gateway connection |
| `/metrics` | GET | Observability snapshot |
