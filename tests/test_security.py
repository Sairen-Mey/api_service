"""Argon2 automatically salts each password independently."""

import asyncio

from app.security import hash_password, verify_password


def test_salt_and_password_verification():
    async def check():
        first = await hash_password("Password1!")
        second = await hash_password("Password1!")
        # $argon2id$...$<random salt>$<digest>
        assert first.startswith("$argon2id$")
        assert first != second
        assert first.split("$")[4] != second.split("$")[4]
        assert await verify_password(first, "Password1!") is True
        assert await verify_password(second, "Wrong1!") is False

    asyncio.run(check())
