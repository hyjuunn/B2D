import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volume import VolumeWeightedAveragePrice
from binance.client import Client
from app.core.config import settings
from typing import Dict, Any

class TechnicalAnalyzer:
    _client = None
    
    @classmethod
    def _get_client(cls):
        if not cls._client:
            cls._client = Client(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
        return cls._client
    
    @classmethod
    async def get_market_data(cls, symbol: str, position_data: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Get market data including technical indicators and position information
        """
        try:
            client = cls._get_client()
            
            # Get klines data for technical analysis
            klines = client.futures_klines(symbol=symbol, interval='1h', limit=100)
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
                                             'taker_buy_quote', 'ignore'])
            
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # Calculate indicators
            rsi = RSIIndicator(close=df['close'], window=14)
            macd = MACD(close=df['close'])
            ema20 = EMAIndicator(close=df['close'], window=20)
            ema50 = EMAIndicator(close=df['close'], window=50)
            vwap = VolumeWeightedAveragePrice(high=pd.to_numeric(df['high']), 
                                             low=pd.to_numeric(df['low']), 
                                             close=df['close'], 
                                             volume=df['volume'])
            
            # Get position information
            position_info = client.futures_position_information(symbol=symbol)
            position = next((p for p in position_info if float(p['positionAmt']) != 0), None)
            
            if not position:
                position = {
                    'leverage': '1',
                    'liquidationPrice': '0',
                    'marginType': 'isolated',
                    'initialMargin': '0',
                    'maintMargin': '0',
                    'unrealizedProfit': '0'
                }
            
            return {
                'leverage': float(position['leverage']),
                'liquidation_price': float(position['liquidationPrice']),
                'margin_type': position['marginType'],
                'initial_margin': float(position['initialMargin']),
                'maintenance_margin': float(position['maintMargin']),
                'unrealized_pnl': float(position['unrealizedProfit']),
                'indicators': {
                    'rsi': rsi.rsi().iloc[-1],
                    'macd': macd.macd().iloc[-1],
                    'macd_signal': macd.macd_signal().iloc[-1],
                    'ema_20': ema20.ema_indicator().iloc[-1],
                    'ema_50': ema50.ema_indicator().iloc[-1],
                    'volume': df['volume'].iloc[-1],
                    'vwap': vwap.volume_weighted_average_price().iloc[-1]
                }
            }
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error getting market data: {e}")
            return {
                'leverage': 1,
                'liquidation_price': 0,
                'margin_type': 'isolated',
                'initial_margin': 0,
                'maintenance_margin': 0,
                'unrealized_pnl': 0,
                'indicators': {
                    'rsi': 0,
                    'macd': 0,
                    'macd_signal': 0,
                    'ema_20': 0,
                    'ema_50': 0,
                    'volume': 0,
                    'vwap': 0
                }
            } 