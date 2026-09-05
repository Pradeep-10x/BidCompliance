from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import RequireRole, get_current_active_user
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserLogin, UserRead, UserRegister
from app.services.auth_service import authenticate_user, register_user

router = APIRouter()


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserRegister, db: AsyncSession = Depends(get_db)
) -> User:
    return await register_user(db, user_in)


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin, db: AsyncSession = Depends(get_db)
) -> Token:
    user = await authenticate_user(db, login_data.email, login_data.password)
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@router.get("/admin-only")
async def admin_only(
    current_user: User = Depends(RequireRole(UserRole.ADMIN)),
) -> dict[str, str]:
    return {"message": "Admin access granted", "user_id": str(current_user.id)}


@router.get("/officer-only")
async def officer_only(
    current_user: User = Depends(RequireRole(UserRole.OFFICER)),
) -> dict[str, str]:
    return {"message": "Officer access granted", "user_id": str(current_user.id)}
