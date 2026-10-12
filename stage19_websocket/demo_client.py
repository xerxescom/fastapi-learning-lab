"""真实网络客户端：两条连接接收同一条广播，运行前先启动服务。"""

import argparse
import asyncio
import json

from websockets.asyncio.client import connect


async def run(base_url: str) -> None:
    async with connect(f"{base_url}/ws/chat?name=alice", open_timeout=5) as alice:
        async with connect(f"{base_url}/ws/chat?name=bobby", open_timeout=5) as bobby:
            print("alice welcome:", await asyncio.wait_for(alice.recv(), 5))
            print("bobby welcome:", await asyncio.wait_for(bobby.recv(), 5))
            await alice.send(json.dumps({"type": "chat", "text": "Hello FastAPI!"}))
            print("alice received:", await asyncio.wait_for(alice.recv(), 5))
            print("bobby received:", await asyncio.wait_for(bobby.recv(), 5))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 19 双连接演示客户端")
    parser.add_argument("--url", default="ws://127.0.0.1:8000")
    asyncio.run(run(parser.parse_args().url.rstrip("/")))
