"""Initialize database with tables."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.base import Base
from app.db.session import engine
from app.db.models.user import User, ConsentRecord, Appointment


async def init_db():
    """Create all database tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Drop all tables (careful in production!)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
