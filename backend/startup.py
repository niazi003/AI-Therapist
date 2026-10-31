"""Startup script to initialize database and run the application."""
import asyncio
import subprocess
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.base import Base
from app.db.session import engine
from app.db.models.user import (
    User, ConsentRecord, Appointment,
    Conversation, Message, ConversationSummary, UserProfile
)


async def init_db():
    """Create all database tables."""
    try:
        print("Initializing database tables...")
        async with engine.begin() as conn:
            # Create all tables (idempotent - won't recreate existing tables)
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized successfully!")
        print("Tables created:")
        print("  - users")
        print("  - consent_records")
        print("  - appointments")
        print("  - conversations")
        print("  - messages")
        print("  - conversation_summaries")
        print("  - user_profiles")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    # Initialize database
    if not asyncio.run(init_db()):
        sys.exit(1)
    
    # Start uvicorn
    print("Starting application...")
    subprocess.run([
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ], check=True)
