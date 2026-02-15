#!/usr/bin/env python3
"""Run database migrations manually."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db

async def main():
    print("Running database migrations...")
    await init_db()
    print("✅ Migrations complete!")

if __name__ == "__main__":
    asyncio.run(main())
