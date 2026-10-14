from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.database import User, get_db
from app.schemas.common import ApiResponse
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@router.post(
    "/register",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="auth_register"))]
)
def register(req: AuthRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        return ApiResponse.fail(code="USER_EXISTS", message="User with this email already exists.", status_code=400)

    user = User(
        email=req.email.lower(),
        name=req.name,
        password_hash=hash_password(req.password),
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return ApiResponse.ok({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    })


@router.post(
    "/login",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="auth_login"))]
)
def login(req: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return ApiResponse.ok({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    })


@router.get("/me", response_model=ApiResponse[Dict[str, Any]])
def get_me(current_user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        return ApiResponse.ok(current_user)
    return ApiResponse.ok({"id": user.id, "email": user.email, "name": user.name, "role": user.role})
