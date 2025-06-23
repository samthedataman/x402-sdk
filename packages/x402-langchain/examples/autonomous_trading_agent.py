"""Example of an autonomous trading agent that pays for real-time data"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from x402_langchain import X402Client, X402Config, create_x402_agent


class AutonomousTradingAgent:
    """Trading agent that purchases real-time market data"""
    
    def __init__(self, private_key: str, initial_capital: float = 10000.0):
        self.config = X402Config(
            private_key=private_key,
            spending_limits={
                "per_request": 0.50,  # Max $0.50 per data request
                "per_hour": 10.0,     # Max $10/hour on data
                "per_day": 50.0,      # Max $50/day on data
            },
            auto_approve=True,
            allowed_domains=[
                "api.alphawave.example.com",
                "data.quandl.example.com",
                "realtime.iex.example.com",
                "sentiment.newsapi.example.com",
            ],
            log_payments=True,
        )
        
        self.client = X402Client(self.config)
        self.capital = initial_capital
        self.positions: Dict[str, float] = {}
        self.trades_today = 0
        self.pnl = 0.0
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Purchase real-time market data for a symbol"""
        
        # Get price data
        price_url = f"https://realtime.iex.example.com/quote/{symbol}"
        price_result = await self.client.fetch_with_payment(
            url=price_url,
            max_amount=0.10  # $0.10 for price data
        )
        
        # Get sentiment data
        sentiment_url = f"https://sentiment.newsapi.example.com/analysis/{symbol}"
        sentiment_result = await self.client.fetch_with_payment(
            url=sentiment_url,
            max_amount=0.25  # $0.25 for sentiment analysis
        )
        
        # Get technical indicators
        technical_url = f"https://api.alphawave.example.com/indicators/{symbol}"
        technical_result = await self.client.fetch_with_payment(
            url=technical_url,
            max_amount=0.15  # $0.15 for technical data
        )
        
        return {
            "symbol": symbol,
            "price": price_result.data if price_result.success else None,
            "sentiment": sentiment_result.data if sentiment_result.success else None,
            "technical": technical_result.data if technical_result.success else None,
            "data_cost": sum([
                float(price_result.amount),
                float(sentiment_result.amount),
                float(technical_result.amount)
            ])
        }
    
    async def analyze_opportunity(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trading opportunity based on purchased data"""
        
        # Simplified trading logic
        score = 0
        reasons = []
        
        if market_data.get("price"):
            price_data = market_data["price"]
            if price_data.get("rsi", 50) < 30:
                score += 2
                reasons.append("Oversold (RSI < 30)")
            elif price_data.get("rsi", 50) > 70:
                score -= 2
                reasons.append("Overbought (RSI > 70)")
        
        if market_data.get("sentiment"):
            sentiment = market_data["sentiment"]
            if sentiment.get("score", 0) > 0.7:
                score += 1
                reasons.append("Positive sentiment")
            elif sentiment.get("score", 0) < -0.7:
                score -= 1
                reasons.append("Negative sentiment")
        
        if market_data.get("technical"):
            technical = market_data["technical"]
            if technical.get("trend", "neutral") == "bullish":
                score += 1
                reasons.append("Bullish trend")
            elif technical.get("trend", "neutral") == "bearish":
                score -= 1
                reasons.append("Bearish trend")
        
        # Decision
        action = "buy" if score >= 2 else "sell" if score <= -2 else "hold"
        confidence = abs(score) / 4.0  # Max score is 4
        
        return {
            "action": action,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "data_quality": len([v for v in market_data.values() if v]) / 3.0
        }
    
    async def execute_trade(self, symbol: str, action: str, confidence: float):
        """Execute a trade based on analysis"""
        
        # Calculate position size based on confidence
        max_position = self.capital * 0.1  # Max 10% per position
        position_size = max_position * confidence
        
        if action == "buy" and symbol not in self.positions:
            self.positions[symbol] = position_size
            self.capital -= position_size
            self.trades_today += 1
            print(f"📈 BOUGHT {symbol}: ${position_size:.2f} (confidence: {confidence:.1%})")
            
        elif action == "sell" and symbol in self.positions:
            position = self.positions.pop(symbol)
            # Simulate 2% profit/loss randomly for demo
            pnl = position * 0.02 * (1 if confidence > 0.5 else -1)
            self.capital += position + pnl
            self.pnl += pnl
            self.trades_today += 1
            print(f"📉 SOLD {symbol}: ${position:.2f}, P&L: ${pnl:.2f}")
    
    async def run_trading_session(self, symbols: list, duration_minutes: int = 5):
        """Run an automated trading session"""
        
        print(f"\n🤖 Starting Autonomous Trading Session")
        print(f"📊 Initial Capital: ${self.capital:.2f}")
        print(f"💳 Data Budget: ${self.config.spending_limits.per_day:.2f}/day")
        print(f"📈 Symbols: {', '.join(symbols)}")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print("\n")
        
        start_time = datetime.now()
        session_spend = 0.0
        
        while (datetime.now() - start_time).seconds < duration_minutes * 60:
            for symbol in symbols:
                print(f"\n🔍 Analyzing {symbol}...")
                
                try:
                    # Get market data (this costs money!)
                    market_data = await self.get_market_data(symbol)
                    data_cost = market_data["data_cost"]
                    session_spend += data_cost
                    
                    print(f"💰 Data purchased for ${data_cost:.2f}")
                    
                    # Analyze opportunity
                    analysis = await self.analyze_opportunity(market_data)
                    
                    print(f"📊 Analysis: {analysis['action'].upper()} "
                          f"(confidence: {analysis['confidence']:.1%})")
                    print(f"   Reasons: {', '.join(analysis['reasons'])}")
                    
                    # Execute trade if confident
                    if analysis["confidence"] >= 0.5:
                        await self.execute_trade(
                            symbol,
                            analysis["action"],
                            analysis["confidence"]
                        )
                    
                except Exception as e:
                    print(f"❌ Error analyzing {symbol}: {e}")
                
                # Don't hammer the APIs
                await asyncio.sleep(10)
            
            # Status update
            spending_status = self.client.get_spending_status()
            print(f"\n💵 Session spend: ${session_spend:.2f} | "
                  f"Daily remaining: ${spending_status['remaining']['day']:.2f}")
        
        # Final report
        print(f"\n{'='*60}")
        print(f"📊 TRADING SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print(f"💰 Total Data Spend: ${session_spend:.2f}")
        print(f"📈 Trades Executed: {self.trades_today}")
        print(f"💵 Final Capital: ${self.capital:.2f}")
        print(f"📊 Total P&L: ${self.pnl:+.2f}")
        print(f"🏆 ROI: {(self.pnl / 10000.0):.2%}")
        print(f"\n💳 Payment Analytics:")
        print(f"   Total requests: {spending_status['spent_today'] / 0.10:.0f}")
        print(f"   Avg cost per request: ${session_spend / max(self.trades_today, 1):.3f}")


async def main():
    # Configure
    private_key = os.getenv("AGENT_PRIVATE_KEY", "0x...")
    
    # Create trading agent
    agent = AutonomousTradingAgent(
        private_key=private_key,
        initial_capital=10000.0
    )
    
    # Run trading session
    symbols = ["AAPL", "GOOGL", "TSLA", "BTC", "ETH"]
    await agent.run_trading_session(
        symbols=symbols,
        duration_minutes=2  # Short demo session
    )


if __name__ == "__main__":
    asyncio.run(main())