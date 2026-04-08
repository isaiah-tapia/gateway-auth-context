import uuid
import encodings
from datetime import datetime
from abc import ABC, abstractmethod

class AbstractAdapter(ABC):

    channel: str = "abstract"

    @abstractmethod
    def normalize(self, dict):
        """
        This method should be implemented across our kinds of channels
        """
        pass

    @abstractmethod
    def outgoing_denormalize(self, dict):
        """
        Denomralize our response and send it back to our client
        """
        pass

    def sanitize(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return text.replace("\x00", "").strip()[:2000]
    
    def abs_scheme(self, session_id: str, user_id: str, text: str,
                   attachments: list = None, msg_id: str = None):
        """
        base scheme strucure. Should stay the same across our adapters.  
        """
        return {
            "id": msg_id or str(uuid.uuid4()),
            "session_id": session_id,
            "channel": self.channel,
            "user_id": user_id,
            "text": text,
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
            "attachments": attachments or []
        }
    