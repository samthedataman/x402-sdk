"""Example of a multi-agent system with specialized payment roles"""

import asyncio
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from x402_langchain import X402Client, X402Config, create_x402_agent


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    source: str
    cost: float


class ResearchAgent:
    """Agent responsible for finding data sources"""
    
    def __init__(self, llm):
        self.llm = llm
        self.discovered_sources = {}
    
    async def find_data_sources(self, topic: str) -> List[Dict[str, Any]]:
        """Discover x402-enabled data sources for a topic"""
        
        # In production, this would query a registry or marketplace
        mock_sources = {
            "market_data": [
                {
                    "name": "PremiumMarketData",
                    "url": "https://api.marketdata.x402.com/quote",
                    "cost": 0.05,
                    "quality_score": 0.95,
                    "features": ["real-time", "historical", "level-2"]
                },
                {
                    "name": "BudgetMarketFeed", 
                    "url": "https://budget.markets.x402.com/data",
                    "cost": 0.01,
                    "quality_score": 0.70,
                    "features": ["delayed-15min", "basic"]
                }
            ],
            "news_sentiment": [
                {
                    "name": "AINewsSentiment",
                    "url": "https://sentiment.ainews.x402.com/analyze",
                    "cost": 0.10,
                    "quality_score": 0.90,
                    "features": ["ml-powered", "multi-source"]
                }
            ]
        }
        
        sources = mock_sources.get(topic, [])
        self.discovered_sources[topic] = sources
        
        print(f"🔍 Research Agent: Found {len(sources)} sources for '{topic}'")
        for source in sources:
            print(f"   - {source['name']}: ${source['cost']} (quality: {source['quality_score']})")
        
        return sources


class PurchasingAgent:
    """Agent responsible for making payment decisions"""
    
    def __init__(self, x402_client: X402Client, budget: float = 10.0):
        self.client = x402_client
        self.budget = budget
        self.spent = 0.0
        self.purchases = []
    
    async def evaluate_purchase(self, source: Dict[str, Any], urgency: str = "normal") -> bool:
        """Evaluate whether to purchase from a source"""
        
        cost = source["cost"]
        quality = source["quality_score"]
        
        # Decision logic based on budget, quality, and urgency
        if self.spent + cost > self.budget:
            print(f"❌ Purchasing Agent: Over budget (would be ${self.spent + cost:.2f})")
            return False
        
        if urgency == "high" and quality > 0.6:
            return True
        elif urgency == "normal" and quality > 0.8 and cost < 0.10:
            return True
        elif urgency == "low" and quality > 0.9 and cost < 0.05:
            return True
        
        print(f"🤔 Purchasing Agent: Skipping {source['name']} (cost/quality trade-off)")
        return False
    
    async def purchase_data(self, source: Dict[str, Any]) -> Any:
        """Execute purchase from a source"""
        
        print(f"💳 Purchasing Agent: Buying from {source['name']} for ${source['cost']}")
        
        try:
            result = await self.client.fetch_with_payment(
                url=source["url"],
                max_amount=source["cost"] * 1.1  # 10% buffer
            )
            
            if result.success:
                self.spent += source["cost"]
                self.purchases.append({
                    "source": source["name"],
                    "cost": source["cost"],
                    "timestamp": datetime.utcnow()
                })
                print(f"✅ Purchase successful! Total spent: ${self.spent:.2f}")
                return result.data
            else:
                print(f"❌ Purchase failed: {result.error}")
                return None
                
        except Exception as e:
            print(f"❌ Purchase error: {e}")
            return None


class AnalysisAgent:
    """Agent responsible for analyzing purchased data"""
    
    def __init__(self, llm):
        self.llm = llm
        self.analyses = []
    
    async def analyze_data(self, data_points: List[MarketData]) -> Dict[str, Any]:
        """Analyze collected market data"""
        
        if not data_points:
            return {"error": "No data to analyze"}
        
        # Calculate metrics
        avg_price = sum(d.price for d in data_points) / len(data_points)
        total_volume = sum(d.volume for d in data_points)
        price_variance = sum((d.price - avg_price) ** 2 for d in data_points) / len(data_points)
        
        # Sentiment from different sources
        sources = list(set(d.source for d in data_points))
        
        analysis = {
            "summary": {
                "data_points": len(data_points),
                "sources": sources,
                "avg_price": avg_price,
                "total_volume": total_volume,
                "price_variance": price_variance,
                "volatility": "high" if price_variance > 100 else "normal"
            },
            "recommendation": self._generate_recommendation(avg_price, price_variance),
            "confidence": min(0.95, len(data_points) * 0.2)  # More data = higher confidence
        }
        
        self.analyses.append(analysis)
        return analysis
    
    def _generate_recommendation(self, price: float, variance: float) -> str:
        """Generate trading recommendation"""
        if variance > 100:
            return "HOLD - High volatility detected"
        elif price < 50:
            return "BUY - Undervalued opportunity"
        else:
            return "MONITOR - Stable conditions"


class CoordinatorAgent:
    """Master agent that coordinates the multi-agent system"""
    
    def __init__(self, private_key: str):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Initialize x402 client
        config = X402Config(
            private_key=private_key,
            spending_limits={
                "per_request": 0.20,
                "per_hour": 2.00,
                "per_day": 10.00
            }
        )
        
        # Initialize specialized agents
        self.research_agent = ResearchAgent(self.llm)
        self.purchasing_agent = PurchasingAgent(X402Client(config), budget=1.0)
        self.analysis_agent = AnalysisAgent(self.llm)
    
    async def execute_research_task(self, symbol: str, urgency: str = "normal"):
        """Execute a complete research task"""
        
        print(f"\n{'='*60}")
        print(f"🎯 Coordinator: Starting research task for {symbol}")
        print(f"   Urgency: {urgency}")
        print(f"   Budget: ${self.purchasing_agent.budget:.2f}")
        print(f"{'='*60}\n")
        
        # Step 1: Research sources
        market_sources = await self.research_agent.find_data_sources("market_data")
        sentiment_sources = await self.research_agent.find_data_sources("news_sentiment")
        
        all_sources = market_sources + sentiment_sources
        
        # Step 2: Evaluate and purchase
        purchased_data = []
        
        for source in all_sources:
            should_buy = await self.purchasing_agent.evaluate_purchase(source, urgency)
            
            if should_buy:
                data = await self.purchasing_agent.purchase_data(source)
                if data:
                    # Mock data transformation
                    market_data = MarketData(
                        symbol=symbol,
                        price=data.get("price", 100.0),
                        volume=data.get("volume", 1000000),
                        timestamp=datetime.utcnow(),
                        source=source["name"],
                        cost=source["cost"]
                    )
                    purchased_data.append(market_data)
        
        # Step 3: Analyze
        if purchased_data:
            analysis = await self.analysis_agent.analyze_data(purchased_data)
            
            print(f"\n📊 Analysis Complete:")
            print(f"   Data points: {analysis['summary']['data_points']}")
            print(f"   Average price: ${analysis['summary']['avg_price']:.2f}")
            print(f"   Volatility: {analysis['summary']['volatility']}")
            print(f"   Recommendation: {analysis['recommendation']}")
            print(f"   Confidence: {analysis['confidence']:.1%}")
        else:
            print("\n❌ No data purchased - unable to analyze")
        
        # Summary
        print(f"\n💰 Financial Summary:")
        print(f"   Total spent: ${self.purchasing_agent.spent:.2f}")
        print(f"   Remaining budget: ${self.purchasing_agent.budget - self.purchasing_agent.spent:.2f}")
        print(f"   Purchases made: {len(self.purchasing_agent.purchases)}")
        
        return {
            "symbol": symbol,
            "analysis": analysis if purchased_data else None,
            "spent": self.purchasing_agent.spent,
            "purchases": self.purchasing_agent.purchases
        }


async def main():
    """Run multi-agent demonstration"""
    
    # Get private key from environment
    private_key = os.getenv("AGENT_PRIVATE_KEY", "0x" + "1" * 64)
    
    # Create coordinator
    coordinator = CoordinatorAgent(private_key)
    
    # Execute research tasks with different urgency levels
    tasks = [
        ("AAPL", "high"),    # High urgency - will buy more expensive sources
        ("GOOGL", "normal"), # Normal urgency - balanced approach
        ("TSLA", "low"),     # Low urgency - only cheapest/best sources
    ]
    
    for symbol, urgency in tasks:
        result = await coordinator.execute_research_task(symbol, urgency)
        await asyncio.sleep(2)  # Pause between tasks
    
    print(f"\n{'='*60}")
    print("🏁 Multi-Agent System Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())