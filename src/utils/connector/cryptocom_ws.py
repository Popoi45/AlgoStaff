import asyncio
import hmac
import json
import time
from datetime import datetime
from .base_ws import BaseWs
from websockets.exceptions import ConnectionClosedError
import websockets
import logging
from utils.functions import send_to_telegram
from config import TEST_MODE

logger = logging.getLogger(__name__)


class CryptocomWs(BaseWs):
    def __init__(self, shutdown_event, topics=None, handler=None):
        super().__init__(shutdown_event, topics=topics, handler=handler)
        self.url = "wss://stream.crypto.com/exchange/v1/market"
        self.topics = topics
        self.handler = handler or self.on_message
        self.ws = None
        self.is_connected = False
        self.keep_alive_task = None
        self.shutdown_event: asyncio.Event = shutdown_event
        self.heartbit_id = None
        self.forced_close = False

    async def connect(self):
        while not self.shutdown_event.is_set() and not self.forced_close:
            try:
                async with websockets.connect(self.url, ping_interval=15, ping_timeout=10) as ws:
                    self.ws = ws
                    self.is_connected = True
                    await self.on_open()
                    # self.keep_alive_task = asyncio.create_task(self.keep_alive())
                    async for message in ws:
                        try:
                            await self.on_message(message)
                        except Exception:
                            logger.exception("Exception in handler")
                            break
            except ConnectionClosedError as cce:
                # Это ожидаемое событие: соединение просто было закрыто без корректного close frame
                logger.warning("Websocket connection closed unexpectedly: %s", cce)
                self.is_connected = False
                # Можем сделать небольшую задержку и переподключиться
                await asyncio.sleep(1)
                continue
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
        await asyncio.sleep(1)
        await self.subscribe_to_topics(self.topics)

    async def on_error(self, error):
        logger.error("On Error:", exc_info=(type(error), error, error.__traceback__))

    async def on_close(self, ws, status, msg):
        logger.info("Time:", datetime.now(), 'on_close', ws, status, msg)
        self.is_connected = False

    async def on_message(self, msg):
        raw_data = json.loads(msg)
        if 'method' not in raw_data:
            return
        logger.debug(f"Default Handler: {raw_data}\n===============")
        if raw_data.get('method') == 'public/heartbeat':
            self.heartbit_id = raw_data['id']
            response_beat = {"id": self.heartbit_id, "method": "public/respond-heartbeat"}
            await self.ws.send(json.dumps(response_beat))
            return
        else:
            await self.handler(msg)

    async def subscribe_to_topics(self, topics):
        params = {"channels": topics}
        if topics and self.is_connected:
            data = {"id": 12321556,
                    "method": "subscribe",
                    "params": params,
                    "nonce": int(time.time() * 1000)}
            await self.ws.send(json.dumps(data))

    async def unsubscribe_from_topics(self, topics):
        params = {"channels": topics}
        if topics and self.is_connected:
            data = {"id": 12321551,
                    "method": "unsubscribe",
                    "params": params,
                    "nonce": int(time.time() * 1000)}
            await self.ws.send(json.dumps(data))

    async def disconnect(self):
        if self.is_connected:
            await self.ws.close()
            self.forced_close = True
            self.is_connected = False
            logger.info("Disconnected WebSocket")

