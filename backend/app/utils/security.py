import base64
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import get_settings

settings = get_settings()
security_bearer = HTTPBearer(auto_error=False)


PASSWORD_HASH_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return "$".join((
        "pbkdf2_sha256",
        str(PASSWORD_HASH_ITERATIONS),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iteration_count = int(iterations)
        if not PASSWORD_HASH_ITERATIONS <= iteration_count <= 2_000_000:
            return False
        salt_bytes = base64.urlsafe_b64decode(salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt_bytes, iteration_count
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(data: Dict[str, Any], expires_in_seconds: int = 86400 * 7) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds
    payload["iat"] = int(time.time())
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Optional[Dict[str, Any]]:
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub") or payload.get("id") or payload.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        return None
    email = payload.get("email", "")
    return {"id": user_id, "email": email, "role": payload.get("role", "user")}


async def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid."
        )
    return user


PRIVILEGED_ROLES = frozenset({"admin", "lead_analyst"})


async def get_privileged_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    user_role = current_user.get("role", "")
    if user_role not in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative or lead analyst privileges required for platform catalog mutations."
        )
    return current_user
