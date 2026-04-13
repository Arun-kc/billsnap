"""
Seed script — inserts the two V1 users into the database.

Run once after `alembic upgrade head`:

    python scripts/seed.py

Requires DATABASE_URL to be set in .env (or the environment).
Idempotent: skips rows whose phone number already exists.
"""
import asyncio
import sys
import uuid
from pathlib import Path

# Make sure the project root is on the path when run directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.user import User

USERS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Shop Owner",          # Arun's father — update name if you like
        "phone": "+919400000001",       # placeholder — update to real number
        "role": "owner",
        "is_active": True,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Arun",
        "phone": "+919400000002",       # placeholder — update to real number
        "role": "admin",
        "is_active": True,
    },
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for data in USERS:
            result = await session.execute(
                select(User).where(User.phone == data["phone"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  skip  {data['role']} ({data['phone']}) — already exists")
                continue

            user = User(**data)
            session.add(user)
            print(f"  insert {data['role']} ({data['name']}, {data['phone']})")

        await session.commit()

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
