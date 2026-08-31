import hashlib, secrets, datetime
import jwt
from .config import settings

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(8)
    return salt + "$" + hashlib.sha256((salt + pw).encode()).hexdigest()

def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
        return hashlib.sha256((salt + pw).encode()).hexdigest() == h
    except Exception:
        return False

def make_token(user_id: str, role: str, workspace_id: str) -> str:
    payload = {
        "sub": user_id, "role": role, "ws": workspace_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def parse_token(token: str):
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

def gen_api_key() -> str:
    return "ak_live_" + secrets.token_hex(16)
