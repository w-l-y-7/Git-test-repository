"""安全模块：密码加密、JWT 登录凭证、识别当前用户

三件事：
1. 密码绝不明文存库，用 bcrypt 单向加密（不可逆，数据库被拖库也解不出密码）
2. 登录成功发一个 JWT token 给浏览器，之后每次请求带上它，服务器验签认人
3. get_current_user：从请求头里的 token 解析出"当前是哪个用户"
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import SECRET_KEY, TOKEN_EXPIRE_HOURS
from .database import get_db
from .db_models import User

# HTTPBearer：自动解析请求头里的 "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer()


# ---------- 密码 ----------

def hash_password(password: str) -> str:
    """把明文密码加密成不可逆的密文再存库"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """登录时核对：明文密码 vs 库里存的密文"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ---------- JWT ----------

def create_token(user_id: int, role: str) -> str:
    """给用户签一张"身份证"（JWT），里面写谁 + 有效期"""
    payload = {
        "sub": str(user_id),  # sub = 用户的 id
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """验签并解出身份证内容；过期或伪造都会抛异常"""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


# ---------- 依赖 ----------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """识别当前登录用户：token → 用户 id → 查库返回用户；不合法就 401"""
    try:
        payload = decode_token(credentials.credentials)
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在，请重新登录",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """在 get_current_user 基础上再要求管理员身份，否则 403"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该操作需要管理员权限",
        )
    return current_user
