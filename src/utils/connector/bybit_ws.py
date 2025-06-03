import asyncio
import hmac
import json
import time
import traceback
from datetime import datetime
from .base_ws import BaseWs
import websockets
import logging
from config import TEST_MODE

logger = logging.getLogger(__name__)

class BybitWs(BaseWs):
    def __init__(self, shutdown_event, topics=None, handler=None):
        super().__init__(shutdown_event, topics=topics, handler=handler)
        # self.url = "wss://stream-testnet.bybit.com/v5/public/spot" if TEST_MODE else "wss://stream.bybit.com/v5/public/spot"
        self.url = "wss://stream.bybit.com/v5/public/spot"
        self.topics = topics
        self.handler = handler or self.on_message
        self.ws = None
        self.is_connected = False
        self.keep_alive_task = None
        self.shutdown_event: asyncio.Event = shutdown_event
        self.forced_close = False

    async def connect(self):
        while not self.shutdown_event.is_set() and not self.forced_close:
            try:
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    self.is_connected = True
                    await self.on_open()
                    self.keep_alive_task = asyncio.create_task(self.keep_alive())
                    async for message in ws:
                        try:
                            await self.handler(message)
                        except Exception:
                            logger.exception("Exception in handler")
                            break
            except asyncio.CancelledError:
                logger.info('Connection was closed - CancelledError')
                self.is_connected = False
                break
            except Exception as e:
                logger.exception('Connection error')
                self.is_connected = False
                await self.on_error(e)
                await asyncio.sleep(1)


    async def on_open(self):
        logger.info('Websocket was opened!')
        await self.subscribe_to_topics(self.topics)

    async def on_error(self, error):
        logger.error("On Error:", exc_info=(type(error), error, error.__traceback__))

    async def on_close(self, ws, status, msg):
        logger.info("Time:", datetime.now(), 'on_close', ws, status, msg)
        self.is_connected = False

    async def on_message(self, msg):
        data = json.loads(msg)
        logger.debug(f"Default Handler: {data}\n===============")



    async def subscribe_to_topics(self, topics):
        if isinstance(topics, str): topics = [topics]
        if topics and self.is_connected:
            data = {"op": "subscribe", "args": topics}
            await self.ws.send(json.dumps(data))

    async def unsubscribe_from_topics(self, topics):
        if topics and self.is_connected:
            data = {"op": "unsubscribe", "args": topics}
            await self.ws.send(json.dumps(data))

    async def disconnect(self):
        if self.is_connected:
            await self.ws.close()
            self.forced_close = True
            self.is_connected = False
            logger.info("Disconnected WebSocket")

    async def keep_alive(self):
        while self.is_connected:
            try:
                await asyncio.sleep(300)
                if self.is_connected:
                    data = {"op": "ping"}
                    await self.ws.send(json.dumps(data))
            except asyncio.CancelledError:
                logger.exception('Keep-alive was cancelled')
                break
            except Exception:
                logger.exception('Keep-alive error')
                self.is_connected = False
                break

