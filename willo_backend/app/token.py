import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import jwt

# Ensure environment variables are loaded (noop if already loaded elsewhere)
load_dotenv()

_SECRET_KEY = os.getenv("SECRET_KEY")
if not _SECRET_KEY:
    # Fail fast & loud during startup/import so it's obvious misconfiguration occurred.
    raise RuntimeError("SECRET_KEY environment variable is not set; cannot generate/verify JWT tokens.")

def generate_token(form_id: int, expires_in_minutes: int | None = None) -> str:
    """Generate a JWT token embedding the form_id.

    By default the token does NOT expire (no `exp` claim). If `expires_in_minutes` is provided,
    an expiration will be added.

    Args:
        form_id: The form identifier to embed in the token.
        expires_in_minutes: Optional lifetime in minutes. If None (default) token is non-expiring.
    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "form_id": form_id,
        "iat": int(now.timestamp()),
    }
    if isinstance(expires_in_minutes, (int, float)) and expires_in_minutes > 0:
        payload["exp"] = int((now + timedelta(minutes=expires_in_minutes)).timestamp())
    token = jwt.encode(payload, _SECRET_KEY, algorithm="HS256")
    # PyJWT>=2 returns a str; older versions may return bytes.
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def is_authorized(token: str) -> int | None:
    """Validate token and return embedded form_id if authorized else None.

    Returns:
        form_id (int) if token valid; otherwise None.
    """
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=["HS256"])
        form_id = payload.get("form_id")
        if isinstance(form_id, int):
            return form_id
        return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None