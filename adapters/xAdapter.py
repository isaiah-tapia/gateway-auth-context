import uuid
from datetime import datetime, timezone
from adapters.abstractAdapter import AbstractAdapter

class XDMAdapter(AbstractAdapter):
    """
    X Direct Messages — uses participant_id to identify sender.
    Incoming: { text, participant_id, message_id?, created_timestamp?, attachment_urls? }
    Outgoing: { text, recipient_id }
    """

    channel = "x_dm"

    def normalize(self, raw: dict, session_id: str, user_id: str) -> dict:
        # X uses participant_id instead of user_id
        participant_id = raw.get("participant_id", user_id)

        # X is unix time https://stackoverflow.com/questions/38546630/how-to-interpret-data-time-in-twitter-dm
        created_ts = raw.get("created_timestamp")
        if created_ts:
            datetime.fromtimestamp(int(created_ts) / 1000, tz=timezone.utc).isoformat()
        else:
            timestamp = datetime.now(timezone.utc).isoformat()

        # X attachments are a list of URLs
        attachment_urls = raw.get("attachment_urls", [])
        attachments = [{"type": "url", "url": u} for u in attachment_urls]

        normalized = {
            "id": raw.get("message_id") or str(uuid.uuid4()),
            "session_id": session_id,
            "channel": self.channel,
            "user_id": participant_id,
            "text": self.sanitize(raw.get("text", "")),
            "timestamp": timestamp,
            "attachments": attachments,
            # metadata for denormalize
            "_participant_id": participant_id
        }
        return normalized

    def outgoing_denormalize(self, response: dict) -> dict:
        return {
            "text": response.get("text", ""),
            "recipient_id": response.get("_participant_id", "")
        }