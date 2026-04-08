import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from datetime import timezone 
from typing import Dict, Optional, Set

import jwt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SIGNKEY = "3hfiojf903nfsjdkand"
ALGO = "HS256"
TOKEN_EXPIRY = 15
RATE_LIMIT_SESSION = 10
RATE_LIMIT_WINDOW = 60
MAX_MISSED = 100

class Session():
    """
    Each individual session corresponds to an individual process (i.e a unique user is signed in multiple times across
    devices or apps). 
    """
    def __init__(self, session_id: str, user_id: str, channel: str) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.channel = channel
        self.connected_at =  datetime.now(timezone.utc)
        self.websocket: Optional[WebSocket] = None # our conenction is reachable from here
        self.missed_messages: deque = deque(maxlen=MAX_MISSED)
        self.message_timestamps: deque = deque()

    @property
    def is_connected(self) -> bool:
        return self.websocket is not None

    def empty_old_messages(self, current_time):
        size_msg_ts = len(self.message_timestamps)
        if size_msg_ts < 1:
            return 
        earliest_time = self.message_timestamps[0]
        while earliest_time < current_time - timedelta(seconds=RATE_LIMIT_WINDOW):
            self.message_timestamps.popleft()
            if len(self.message_timestamps) > 0:
                earliest_time = self.message_timestamps[0] 
            else:
                break

    def is_under_rate_limit(self) -> bool:
        """
        Limit our rate limit to under 10 messages per minute.
        """
        current_time = datetime.now(timezone.utc)
        self.empty_old_messages(current_time=current_time)
        self.message_timestamps.append(current_time)
        count_msgs_left = len(self.message_timestamps)
        return True if count_msgs_left < RATE_LIMIT_SESSION else False

class SessionStore():
    """
    We need to keep track of the session which are on going, this is our trusted computing base.
    """

    def __init__(self) -> None:
        # maps a session id to a session
        self._sessions: Dict[str, Session] = {}

    def create(self, user_id: str, channel: str ) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, user_id=user_id, channel=channel)
        self._sessions[session_id] = session
        return session

    def get(self, session_id) -> Session | None:
        session = self._sessions.get(session_id)
        return session
    
    def get_session_by_user(self, user_id) -> set:
        sessions_belonging_to_user = set()
        for _, session in self._sessions.items():
            if session.user_id == user_id:
                sessions_belonging_to_user.add(session)
        return sessions_belonging_to_user

    def attach_websocket(self, session: Session, websocket: WebSocket) -> None:
        session.websocket = websocket

    def detach_websocket(self, session: Session) -> None:
        session.websocket = None

