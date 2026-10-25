import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Header, HTTPException, Request, status

from .config import get_settings
from .schemas import SensorReading


def sign_event(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def encrypt_device_secret(secret: str) -> str:
    key = get_settings().device_encryption_key
    if not key:
        raise RuntimeError("DEVICE_ENCRYPTION_KEY must be configured before registering devices.")
    return Fernet(key.encode("ascii")).encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_device_secret(encrypted: str) -> str:
    key = get_settings().device_encryption_key
    if not key:
        raise RuntimeError("DEVICE_ENCRYPTION_KEY must be configured before accepting readings.")
    try:
        return Fernet(key.encode("ascii")).decrypt(encrypted.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as error:
        raise RuntimeError("Stored device secret cannot be decrypted; verify DEVICE_ENCRYPTION_KEY.") from error


def verify_device_signature(raw_body: bytes, secret: str, supplied: str) -> bool:
    return hmac.compare_digest(sign_event(raw_body, secret), supplied.removeprefix("sha256="))


def issue_dashboard_token(email: str) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be configured before dashboard login is enabled.")
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": email, "exp": expires}, settings.jwt_secret, algorithm="HS256")


def require_dashboard_user(authorization: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise HTTPException(status_code=503, detail="Dashboard authentication is not configured.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Dashboard sign-in required.")
    try:
        claims = jwt.decode(
            authorization[7:],
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.") from error
    return claims["sub"]


async def get_raw_request_body(request: Request) -> bytes:
    return await request.body()
