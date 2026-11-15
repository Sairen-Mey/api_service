"""Registration, login, logout, and password change."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db import engine, get_session
from .models import Base, LoginSession, User
from .schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from .security import hash_password, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For MVP only: create missing tables without a migration system.
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Auth API MVP", lifespan=lifespan)
bearer = HTTPBearer(auto_error=False)


async def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> LoginSession:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = sha256(credentials.credentials.encode()).hexdigest()
    result = await session.execute(
        select(LoginSession).where(
            LoginSession.token_hash == token_hash,
            LoginSession.expires_at > datetime.now(timezone.utc),
        )
    )
    current = result.scalar_one_or_none()
    if current is None:
        raise HTTPException(
            status_code=401,
            detail="Session is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    user = User(email=data.email, password_hash=await hash_password(data.password))
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return user


@app.post("/auth/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    async with session.begin():
        # Lock the user while verifying credentials, so a concurrent password
        # change cannot create a session for an already replaced password.
        result = await session.execute(
            select(User).where(User.email == data.email).with_for_update()
        )
        user = result.scalar_one_or_none()

        if user is None or not await verify_password(user.password_hash, data.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = secrets.token_urlsafe(32)
        session.add(
            LoginSession(
                user_id=user.id,
                token_hash=sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
        )

    return LoginResponse(access_token=token)


@app.post("/auth/logout", status_code=204)
async def logout(
    current: LoginSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
):
    await session.delete(current)
    await session.commit()


@app.post("/auth/password/change", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    current: LoginSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.id == current.user_id).with_for_update()
    )
    user = result.scalar_one()
    if not await verify_password(user.password_hash, data.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = await hash_password(data.new_password)
    # All old tokens stop working after the password is changed.
    await session.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    await session.commit()
