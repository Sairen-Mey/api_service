"""Argon2id password hashing with a fresh random salt for each password."""

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()



async def hash_password(password: str) -> str:
    # Argon2 generates and embeds a new random salt in every encoded hash.
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password_hash: str, password: str) -> bool:
    try:
        return await asyncio.to_thread(_hasher.verify, password_hash, password)
    except VerifyMismatchError:
        return False
