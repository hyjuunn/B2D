from discord_webhook import DiscordWebhook, DiscordEmbed
from app.core.config import settings
from app.services.technical_analysis import TechnicalAnalyzer
from typing import Dict, Any
from datetime import datetime
import asyncio
from loguru import logger

class DiscordNotifier:
    @staticmethod
    async def send_trade_notification(msg: Dict[Any, Any]):
        """
        Send a detailed trade notification to Discord including technical analysis
        """
        try:
            order = msg.get('o', {})
            
            # Create webhook
            webhook = DiscordWebhook(url=settings.DISCORD_WEBHOOK_URL)
            
            # Create embed
            side = "LONG" if order.get('S') == "BUY" else "SHORT"
            color = "00ff00" if side == "LONG" else "ff0000"
            
            embed = DiscordEmbed(
                title=f"🚨 New {side} Position: {order.get('s')}",
                color=color
            )
            
            # Add trade details
            embed.add_embed_field(name="Symbol", value=order.get('s'), inline=True)
            embed.add_embed_field(name="Side", value=side, inline=True)
            embed.add_embed_field(name="Type", value=order.get('o'), inline=True)
            embed.add_embed_field(name="Price", value=f"${order.get('p')}", inline=True)
            embed.add_embed_field(name="Quantity", value=order.get('q'), inline=True)
            embed.add_embed_field(name="Leverage", value=f"{order.get('L')}x", inline=True)
            
            if order.get('pP'):  # PNL data
                embed.add_embed_field(name="Realized PNL", value=f"${order.get('pP')}", inline=True)
            
            # Add timestamp
            embed.set_timestamp(datetime.fromtimestamp(msg.get('T', 0) / 1000))
            
            # Add footer
            embed.set_footer(text="B2D Trading Assistant")
            
            # Add webhook
            webhook.add_embed(embed)
            
            # Send webhook (in a non-blocking way)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, webhook.execute)
            
            logger.info(f"Discord notification sent for {order.get('s')}")
            
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            logger.error(f"Message content: {msg}") 