from openai import OpenAI
from loguru import logger
from app.core.config import settings
from typing import Dict, Any

class TradeAnalyzer:
    _client = None
    
    @classmethod
    def _get_client(cls):
        if not cls._client:
            cls._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._client
    
    @classmethod
    def analyze_trade(cls, trade_data: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Analyze trade data using OpenAI's GPT model to provide trading advice.
        """
        try:
            # Format the trade data for LLM analysis
            prompt = cls._format_trade_prompt(trade_data)
            
            # Get analysis from OpenAI
            response = cls._get_client().chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert crypto futures trading advisor. Analyze the trade and provide specific advice on stop loss and take profit levels based on current market conditions."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "trade_id": trade_data.get("i"),
                "symbol": trade_data.get("s"),
                "analysis": analysis,
                "timestamp": trade_data.get("T")
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trade: {e}")
            return {
                "error": str(e),
                "trade_id": trade_data.get("i")
            }
    
    @staticmethod
    def _format_trade_prompt(trade_data: Dict[Any, Any]) -> str:
        """
        Format trade data into a prompt for the LLM.
        """
        return f"""
        Please analyze this futures trade:
        
        Symbol: {trade_data.get('s')}
        Side: {trade_data.get('S')}
        Position Size: {trade_data.get('q')}
        Entry Price: {trade_data.get('p')}
        
        Provide specific advice on:
        1. Recommended stop loss levels and reasoning
        2. Target take profit levels and reasoning
        3. Key technical levels to watch
        4. Risk management suggestions
        """ 