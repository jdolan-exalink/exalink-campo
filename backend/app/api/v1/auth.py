from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserMe
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == request.email.lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    extra = {"tenant_id": str(user.tenant_id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, extra=extra),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    extra = {"tenant_id": str(user.tenant_id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, extra=extra),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserMe)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
