"""IPython developer shell with top-level await and async database access."""

import uvloop
from IPython import start_ipython
from IPython.core.async_helpers import get_asyncio_loop
from sqlalchemy import text

from .db import SessionLocal, engine


async def check_db() -> int:
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        return result.scalar_one()


def main() -> None:
    # IPython uses an asyncio loop; replace its implementation with uvloop.
    uvloop.install()
    loop = get_asyncio_loop()
    try:
        # Open/check our external resource in the same loop used by IPython.
        loop.run_until_complete(check_db())
        print("Development shell ready. Try: await check_db()")
        start_ipython(argv=["--no-banner"], user_ns={"check_db": check_db})
    finally:
        # Dispose resources on the very same loop used by IPython autoawait.
        if not loop.is_closed():
            try:
                loop.run_until_complete(engine.dispose())
            finally:
                loop.close()


if __name__ == "__main__":
    main()
