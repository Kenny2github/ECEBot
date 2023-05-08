import asyncio
import os
import sys
from pathlib import Path
# parent directory of ECEBot
os.chdir(Path(__file__).resolve().parent.parent)
sys.path.append(os.getcwd())
from ECEBot import done, run

async def main():
    try:
        await run()
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        return
    finally:
        await done()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
