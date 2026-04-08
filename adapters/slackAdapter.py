import uuid
from datetime import datetime, timezone
from adapters.abstractAdapter import AbstractAdapter

class SlackAdapter(AbstractAdapter):
    """
    Slack — messages can belong to threads via thread_ts.
    Incoming: { text, user, thread_ts?, files?, ts }
    Outgoing: { text, thread_ts? }
    """

    channel = "slack"

    def normalize(self, raw: dict, session_id: str, user_id: str) -> dict:
        # Slack sends user in "user" field not "user_id"
        slack_user_id = raw.get("user", user_id)

        # Convert Slack's unix float string timestamp to ISO
        ts = raw.get("ts")
        if ts:
            timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
        else:
            timestamp = datetime.now(timezone.utc).isoformat()

        # Slack uses both "attachments" and "files"
        attachments = raw.get("attachments", []) + raw.get("files", [])

        # Preserve thread_ts for denormalize
        thread_ts = raw.get("thread_ts")

        normalized = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "channel": self.channel,
            "user_id": slack_user_id,
            "text": self.sanitize(raw.get("text", "")),
            "timestamp": timestamp,
            "attachments": attachments,
            # metadata for denormalize
            "_thread_ts": thread_ts
        }
        return normalized

    def outgoing_denormalize(self, response: dict) -> dict:
        result = {"text": response.get("text", "")}
        # Only include thread_ts if it was in the original message
        thread_ts = response.get("_thread_ts")
        if thread_ts:
            result["thread_ts"] = thread_ts
        return result