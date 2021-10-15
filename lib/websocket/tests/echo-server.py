#!/usr/bin/env python

# From https://github.com/aaugustin/websockets/blob/main/example/echo.py

import asyncio
import websockets


async def echo(websocket, path):
    async for message in websocket:
        await websocket.send(message)


async def main():
    async with websockets.serve(echo, "localhost", 8765):
        await asyncio.Future()  # run forever

asyncio.run(main())
