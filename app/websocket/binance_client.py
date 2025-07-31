import websockets
import json
import hmac
import hashlib
import time
import urllib.parse
from loguru import logger
from app.core.config import settings
from app.services.discord_notifier import DiscordNotifier
import asyncio
import aiohttp
from typing import Optional, Dict
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed

class BinanceWebsocketClient:
    _instance = None
    _ws: Optional[websockets.WebSocketClientProtocol] = None
    _market_ws: Optional[websockets.WebSocketClientProtocol] = None
    _listen_key = None
    _running = False
    _current_prices: Dict[str, float] = {
        'ETHUSDT': None,
        'XTZUSDT': None
    }
    _previous_prices: Dict[str, float] = {
        'ETHUSDT': None,
        'XTZUSDT': None
    }
    BASE_URL = "https://fapi.binance.com"
    WS_URL = "wss://fstream.binance.com/ws"
    
    @classmethod
    async def initialize(cls):
        if not cls._instance:
            cls._instance = cls()
            cls._running = True
            
            # Get listen key first
            await cls._get_listen_key()
            
            # Start WebSocket connections
            asyncio.create_task(cls._connect_websocket())
            asyncio.create_task(cls._connect_market_websocket())
            
            # Start listen key keepalive
            asyncio.create_task(cls._keepalive_listen_key())
            
            # Start price notification task
            asyncio.create_task(cls._send_periodic_price_updates())
            
            logger.info("Binance WebSocket client initialized")
    
    @classmethod
    async def cleanup(cls):
        cls._running = False
        if cls._ws:
            await cls._ws.close()
        if cls._market_ws:
            await cls._market_ws.close()
        if cls._listen_key:
            await cls._delete_listen_key()
        logger.info("Binance WebSocket connections closed")
    
    @classmethod
    async def _get_listen_key(cls):
        """Get listen key for user data stream"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{cls.BASE_URL}/fapi/v1/listenKey",
                headers={"X-MBX-APIKEY": settings.BINANCE_API_KEY}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    cls._listen_key = data["listenKey"]
                    logger.info("Got new listen key")
                else:
                    raise Exception(f"Failed to get listen key: {await response.text()}")
    
    @classmethod
    async def _keepalive_listen_key(cls):
        """Keep listen key alive"""
        while cls._running:
            try:
                if cls._listen_key:
                    async with aiohttp.ClientSession() as session:
                        async with session.put(
                            f"{cls.BASE_URL}/fapi/v1/listenKey",
                            headers={"X-MBX-APIKEY": settings.BINANCE_API_KEY}
                        ) as response:
                            if response.status == 200:
                                logger.debug("Listen key keepalive success")
                            else:
                                logger.error(f"Listen key keepalive failed: {await response.text()}")
                                await cls._get_listen_key()
            except Exception as e:
                logger.error(f"Error in keepalive: {e}")
            
            await asyncio.sleep(30 * 60)  # Every 30 minutes
    
    @classmethod
    async def _delete_listen_key(cls):
        """Delete listen key"""
        if cls._listen_key:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{cls.BASE_URL}/fapi/v1/listenKey",
                    headers={"X-MBX-APIKEY": settings.BINANCE_API_KEY}
                ) as response:
                    if response.status == 200:
                        logger.info("Listen key deleted")
                    else:
                        logger.error(f"Failed to delete listen key: {await response.text()}")
    
    @classmethod
    async def _connect_websocket(cls):
        """Maintain WebSocket connection"""
        while cls._running:
            try:
                async with websockets.connect(f"{cls.WS_URL}/{cls._listen_key}") as websocket:
                    cls._ws = websocket
                    logger.info("WebSocket connected")
                    
                    while cls._running:
                        try:
                            message = await websocket.recv()
                            await cls._handle_message(json.loads(message))
                        except websockets.ConnectionClosed:
                            break
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(5)  # Wait before reconnecting
    
    @classmethod
    async def _handle_message(cls, msg: dict):
        """Handle incoming WebSocket messages"""
        try:
            if msg.get('e') == 'ORDER_TRADE_UPDATE':
                order = msg.get('o', {})
                status = order.get('X')  # Order status
                
                if status in ['FILLED', 'PARTIALLY_FILLED']:
                    await DiscordNotifier.send_trade_notification(msg)
                    logger.info(f"Trade notification sent for order: {order.get('i')}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Message content: {msg}")
    
    @classmethod
    async def _connect_market_websocket(cls):
        """Maintain market data WebSocket connection"""
        while cls._running:
            try:
                # Connect to multiple streams
                streams = ["ethusdt@aggTrade", "xtzusdt@aggTrade"]
                stream_path = "/".join(streams)
                async with websockets.connect(f"{cls.WS_URL}/{stream_path}") as websocket:
                    cls._market_ws = websocket
                    logger.info("Market WebSocket connected")
                    
                    # Subscribe to streams
                    subscribe_msg = {
                        "method": "SUBSCRIBE",
                        "params": streams,
                        "id": 1
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    while cls._running:
                        try:
                            message = await websocket.recv()
                            await cls._handle_market_message(json.loads(message))
                        except websockets.ConnectionClosed:
                            break
                        except Exception as e:
                            logger.error(f"Error handling market message: {e}")
                            
            except Exception as e:
                logger.error(f"Market WebSocket connection error: {e}")
                await asyncio.sleep(5)  # Wait before reconnecting

    @classmethod
    async def _handle_market_message(cls, msg: dict):
        """Handle market data messages"""
        try:
            if msg.get('e') == 'aggTrade':
                symbol = msg.get('s', '').upper()  # Get symbol from message
                if symbol in cls._current_prices:
                    # Store previous price before updating
                    cls._previous_prices[symbol] = cls._current_prices[symbol]
                    cls._current_prices[symbol] = float(msg.get('p', 0))
        except Exception as e:
            logger.error(f"Error processing market message: {e}")
            logger.error(f"Message content: {msg}")

    @classmethod
    def _get_price_emoji(cls, symbol: str) -> str:
        """Get emoji based on price movement"""
        current = cls._current_prices[symbol]
        previous = cls._previous_prices[symbol]
        
        if previous is None or current is None:
            return "💰"  # Default emoji if no comparison possible
        
        if current > previous:
            return "💰📈⬆️"  # Up movement
        elif current < previous:
            return "💰📉⬇️"  # Down movement
        else:
            return "💰"  # No change

    @classmethod
    async def _send_periodic_price_updates(cls):
        """Send price updates every three minutes"""
        while cls._running:
            try:
                # Only send if we have at least one price
                if any(price is not None for price in cls._current_prices.values()):
                    # Create webhook
                    webhook = DiscordWebhook(url=settings.DISCORD_WEBHOOK_URL)
                    
                    # Create embed
                    embed = DiscordEmbed(
                        title="💰 Price Updates",
                        color="0000ff"
                    )
                    
                    # Add price details for each symbol
                    for symbol, price in cls._current_prices.items():
                        if price is not None:
                            emoji = cls._get_price_emoji(symbol)
                            value_text = f"${price:,.4f}"
                            
                            # Add percentage change if previous price exists
                            if cls._previous_prices[symbol] is not None:
                                pct_change = ((price - cls._previous_prices[symbol]) / cls._previous_prices[symbol]) * 100
                                value_text += f"\n({pct_change:+.2f}%)"
                            
                            embed.add_embed_field(
                                name=f"{emoji} {symbol}",
                                value=value_text,
                                inline=True
                            )
                    
                    # Add timestamp
                    embed.set_timestamp(datetime.now())
                    
                    # Add footer
                    embed.set_footer(text="B2D Trading Assistant")
                    
                    # Add webhook
                    webhook.add_embed(embed)
                    
                    # Send webhook
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, webhook.execute)
                    
                    logger.debug("Sent price updates")
                
            except Exception as e:
                logger.error(f"Error sending price update: {e}")
            
            await asyncio.sleep(180)  # Wait for 3 minutes 