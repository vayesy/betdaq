import asyncio
import logging
import sys
from betdaq.aapi.client import BetdaqAsyncClient


async def main():
    logging.basicConfig(level='DEBUG', format='[%(asctime)s %(levelname)s %(name)s] %(message)s')

    loop = asyncio.get_event_loop()
    cli = BetdaqAsyncClient(loop)
    await cli.run_receive()


sys.exit(asyncio.run(main()))
