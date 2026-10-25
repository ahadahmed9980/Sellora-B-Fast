import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from app.config import JWT_ALGORITHM, JWT_SECRET


# access token
def createAccessToken(user_id, session_id) -> str:
    payload = {
        "id": str(user_id),
        "session_id": session_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# createRefreshToken
def createRefreshToken(user_id, session_id):
    payload = {
        "id": str(user_id),
        "sessionId": str(session_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


# hash refresh token
def refreshTokenHash(refreshToken: str) -> str:
    return hashlib.sha256(refreshToken.encode("utf8")).hexdigest()
