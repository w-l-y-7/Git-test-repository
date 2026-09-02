"""认证接口：注册、登录、查当前用户、改密码"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .db_models import User
from .models import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageOut,
    RegisterRequest,
    UserOut,
)
from .security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _to_user_out(user: User) -> UserOut:
    """把数据库里的用户对象转成对外返回的结构（自动去掉密码字段）"""
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.post("/register", response_model=UserOut)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户：用户名唯一，密码加密存储，默认是普通用户"""
    username = req.username.strip()
    if not username or len(req.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能为空，密码至少 6 位",
        )

    user = User(username=username, password_hash=hash_password(req.password), role="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被占用，换一个试试",
        )
    db.refresh(user)
    return _to_user_out(user)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """登录：验证用户名密码，成功返回 token 和用户信息"""
    user = db.query(User).filter(User.username == req.username.strip()).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_token(user.id, user.role)
    return LoginResponse(token=token, user=_to_user_out(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """查当前登录用户是谁（前端刷新页面后用它恢复登录状态）"""
    return _to_user_out(current_user)


@router.post("/change-password", response_model=MessageOut)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码：先核对旧密码，再设置新密码"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少 6 位")

    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return MessageOut(message="密码修改成功")
