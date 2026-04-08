from endpoint.session import SessionStore
from endpoint.auth import create_token, auth_token
from adapters.webAdapter import WebAdapter
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import logging
import asyncio
from adapters.xAdapter import XDMAdapter
from adapters.slackAdapter import SlackAdapter
from websocket.metrics import Metrics
import time
from datetime import datetime, timezone
from websocket.context import augment

ADAPTERS = {
    "web": WebAdapter(),
    "slack": SlackAdapter(),
    "x_dm": XDMAdapter()
}

logger = logging.getLogger("gateway")
app = FastAPI(title="gateway")
sessionStore = SessionStore()
adapter = WebAdapter()
metrics = Metrics()

class TokenRequest(BaseModel):
    user_id: str

async def orchestrator_stub(message: dict) -> str:
    await asyncio.sleep(2)
    context = message.get("context")
    if context:
        return f"[AI response to: '{message['text']}' | context used: {message['context_ids']}]"
    return f"[AI response to: '{message['text']}' | no context found]"

@app.get("/metrics")
def get_metrics():
    return {
        "active_connections": sum(1 for s in sessionStore._sessions.values() if s.websocket is not None),
        "total_sessions": len(sessionStore._sessions),
        "messages_received": metrics.messages_received,
        "messages_delivered": metrics.messages_delivered,
        "auth_failures": metrics.auth_failures,
        "avg_latency_ms": round(metrics.avg_latency(), 2)
    }

@app.post("/auth/token")
def take_user_return_jwt(req: TokenRequest) -> dict:
    token = create_token(user_id=req.user_id)
    return {"token": token}

@app.websocket("/ws")
async def handle_websocket_connections(websocket: WebSocket) -> None:
    """
    This funciton will handle our websocket connections.
    """
    await websocket.accept()
    try:
        data_string = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
    except asyncio.TimeoutError:
        await websocket.close(code=4008, reason="handshake timeout")
        return
    data_dict = json.loads(data_string)
    token = data_dict.get("token")
    authenticated_dic = auth_token(token=token)

    if authenticated_dic is None:
        metrics.auth_failures += 1
        logger.info(json.dumps({"event": "rejected", "reason": "invalid_token", "timestamp": datetime.now(timezone.utc).isoformat()}))
        await websocket.close(code=401, reason="unauthorized, token is invalid")
        return
    
    # get our user's key things
    user_id = authenticated_dic.get("sub")
    session_id = data_dict.get("session_id")
    valid_session = sessionStore.get(session_id)
    channel = data_dict.get("channel")

    # ensure the validity of our session
    if valid_session and valid_session.user_id == user_id:
        # Resume our session
        sessionStore.attach_websocket(session=valid_session, websocket=websocket)
        logger.info(json.dumps({"event": "reconnected", "user_id": user_id, "session_id": valid_session.session_id}))
    else:
        valid_session = sessionStore.create(user_id=user_id, channel=channel)
        sessionStore.attach_websocket(session=valid_session, websocket=websocket)
        logger.info(json.dumps({"event": "connected", "user_id": user_id, "session_id": valid_session.session_id, "channel": channel}))

    # send back to client an acknowledgement, session_id and channel (handshake)
    ack = json.dumps({"ack":1,"session_id":valid_session.session_id,"channel":channel})
    await websocket.send_text(ack)
    metrics.messages_delivered += 1
    while len(valid_session.missed_messages) != 0:
        await websocket.send_text(json.dumps(valid_session.missed_messages.popleft()))
        metrics.messages_delivered += 1
    try:
        while True:
            # check rate limiting
            data = await websocket.receive_text()
            metrics.messages_received += 1
            logger.info(json.dumps({"event": "received", "session_id": valid_session.session_id, "channel": channel}))
            under_rate_limit = valid_session.is_under_rate_limit()
            if under_rate_limit:
                adapter = ADAPTERS.get(channel, WebAdapter())
                unified_schema = adapter.normalize(raw=json.loads(data), session_id=valid_session.session_id, user_id=user_id)
                start = time.time()
                augmented = augment(unified_schema)
                response_text = await orchestrator_stub(augmented)
                latency_ms = (time.time() - start) * 1000
                metrics.record_latency(latency_ms)
                # ADD my missed messages
                if valid_session.is_connected:
                    await websocket.send_text(json.dumps({"response": response_text}))
                    logger.info(json.dumps({"event": "delivered", "session_id": valid_session.session_id, "channel": channel}))
                    metrics.messages_delivered += 1
                else:
                    valid_session.missed_messages.append({"response": response_text})
            else:
                await websocket.send_text(json.dumps({"error": "rate_limited"}))
                metrics.messages_delivered += 1
                continue
    except WebSocketDisconnect:
        logger.info(json.dumps({"event": "disconnected", "session_id": valid_session.session_id}))
        sessionStore.detach_websocket(valid_session)