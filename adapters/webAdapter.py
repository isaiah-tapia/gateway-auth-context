from adapters.abstractAdapter import AbstractAdapter
from datetime import datetime, timezone
import uuid


class WebAdapter(AbstractAdapter):
    """
    Our web adapter should be 
    """
    def __init__(self):
        self.channel = "web"
        super().__init__()

    def normalize(self, raw: dict, session_id: str, user_id: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "channel": self.channel,
            "user_id": user_id,
            "text": self.sanitize(raw.get("text", "")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attachments": raw.get("attachments", [])
        }
    
    def outgoing_denormalize(self, raw: dict) -> dict:
        return {
            "text": raw.get("text", ""),
            "timestamp": raw.get("timestamp", None)
        }   