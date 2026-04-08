from typing import Any, Optional 
from datetime import datetime, timedelta, timezone
import jwt

from endpoint.session import SIGNKEY
from endpoint.session import TOKEN_EXPIRY

"""
Authenticate/create our token for a client, this is seperate from our sesson file as we should differentiate between the 
two instances of verification.
"""

ALGO = "HS256"
def create_token(user_id: str) -> str:
    """
    Our token within this context are our jwt
    user_id: user_id generated prior

    returns: JWT as a string
    """

    # token expiry is 15 minutes from instantiation
    payload = {"sub":user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY), "iat":datetime.now(timezone.utc)}
    token = jwt.encode(payload=payload,algorithm=ALGO, key=SIGNKEY)

    return token

def auth_token(token: str) -> None | dict[str, Any]:
    """
    Take in and authenticates a token. Returns a dictionary with user_id, expieration and iat.
    """
    try:
        dic = jwt.decode(jwt=token,key=SIGNKEY,algorithms=[ALGO])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    return dic

