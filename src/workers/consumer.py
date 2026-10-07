import asyncio
import logging

from src.app.consumer import app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(app.run())
