"""Example of an agent that aggregates data from multiple paid APIs"""

import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from x402_langchain import create_x402_agent, X402Config, X402Client


class APIAggregatorAgent:
    """Agent that intelligently aggregates data from multiple paid sources"""
    
    def __init__(self, private_key: str):
        self.config = X402Config(
            private_key=private_key,
            spending_limits={
                "per_request": 0.50,
                "per_hour": 5.00,
                "per_day": 20.00
            },
            auto_approve=False,
            approval_callback=self.approve_payment,
            log_payments=True
        )
        
        self.client = X402Client(self.config)
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.total_value_obtained = 0.0
        
    async def approve_payment(self, url: str, amount: float) -> bool:
        """Smart payment approval logic"""
        
        # Always approve small amounts
        if amount <= 0.01:
            print(f"✅ Auto-approved micro-payment: ${amount} to {url}")
            return True
        
        # Check ROI for known good sources
        trusted_sources = {
            "api.premium-weather.x402.com": 0.95,  # 95% satisfaction rate
            "data.financial-insights.x402.com": 0.90,
            "ml.predictions.x402.com": 0.85,
        }
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        if domain in trusted_sources:
            satisfaction = trusted_sources[domain]
            if amount <= 0.10 and satisfaction > 0.85:
                print(f"✅ Approved payment to trusted source: ${amount} to {domain}")
                return True
        
        # For unknown sources, be more careful
        if amount > 0.20:
            print(f"❌ Rejected expensive payment: ${amount} to {url}")
            return False
        
        # Default: approve moderate amounts
        print(f"✅ Approved payment: ${amount} to {url}")
        return True
    
    async def get_weather_forecast(self, location: str) -> Dict[str, Any]:
        """Get weather forecast from multiple sources and aggregate"""
        
        print(f"\n🌤️  Fetching weather for {location}...")
        
        sources = [
            {
                "name": "Premium Weather",
                "url": f"https://api.premium-weather.x402.com/forecast?location={location}",
                "max_amount": 0.05
            },
            {
                "name": "Budget Weather",
                "url": f"https://budget-weather.x402.com/basic?city={location}",
                "max_amount": 0.01
            }
        ]
        
        results = []
        
        for source in sources:
            try:
                result = await self.client.fetch_with_payment(
                    url=source["url"],
                    max_amount=source["max_amount"]
                )
                
                if result.success:
                    results.append({
                        "source": source["name"],
                        "data": result.data,
                        "cost": float(result.amount)
                    })
                    self.total_value_obtained += source["max_amount"] * 2  # Assume 2x value
                    
            except Exception as e:
                print(f"   ❌ Failed to fetch from {source['name']}: {e}")
        
        # Aggregate results
        if results:
            return self._aggregate_weather_data(results)
        else:
            return {"error": "No weather data available"}
    
    async def get_financial_insights(self, symbol: str) -> Dict[str, Any]:
        """Get financial insights from multiple premium sources"""
        
        print(f"\n💰 Fetching financial insights for {symbol}...")
        
        sources = [
            {
                "name": "Technical Analysis API",
                "url": f"https://data.financial-insights.x402.com/technical/{symbol}",
                "max_amount": 0.10,
                "priority": "high"
            },
            {
                "name": "Sentiment Analysis API",
                "url": f"https://sentiment.markets.x402.com/analyze/{symbol}",
                "max_amount": 0.08,
                "priority": "medium"
            },
            {
                "name": "ML Predictions API",
                "url": f"https://ml.predictions.x402.com/forecast/{symbol}",
                "max_amount": 0.15,
                "priority": "high"
            }
        ]
        
        # Sort by priority and cost-effectiveness
        sources.sort(key=lambda x: (x["priority"] != "high", x["max_amount"]))
        
        insights = {}
        total_cost = 0.0
        
        for source in sources:
            # Check if we have budget
            remaining_budget = self.config.spending_limits.per_request - total_cost
            if remaining_budget < source["max_amount"]:
                print(f"   ⚠️  Skipping {source['name']} - would exceed request limit")
                continue
            
            try:
                result = await self.client.fetch_with_payment(
                    url=source["url"],
                    max_amount=source["max_amount"]
                )
                
                if result.success:
                    insights[source["name"]] = result.data
                    total_cost += float(result.amount)
                    self.total_value_obtained += source["max_amount"] * 3  # High value data
                    
            except Exception as e:
                print(f"   ❌ Failed to fetch from {source['name']}: {e}")
        
        return {
            "symbol": symbol,
            "insights": insights,
            "total_cost": total_cost,
            "sources_used": len(insights),
            "analysis": self._analyze_financial_data(insights)
        }
    
    async def create_comprehensive_report(self, query: str) -> str:
        """Create a comprehensive report by aggregating multiple data sources"""
        
        print(f"\n📊 Creating comprehensive report for: {query}")
        print("="*60)
        
        # Parse the query to extract relevant parameters
        # In production, use NLP to extract entities
        
        report_sections = []
        
        # Section 1: Weather data (if location mentioned)
        if "weather" in query.lower() or "forecast" in query.lower():
            weather_data = await self.get_weather_forecast("New York")
            report_sections.append({
                "title": "Weather Forecast",
                "content": weather_data
            })
        
        # Section 2: Financial data (if stock symbol mentioned)
        if any(symbol in query.upper() for symbol in ["AAPL", "GOOGL", "TSLA"]):
            symbol = "AAPL"  # Default for demo
            financial_data = await self.get_financial_insights(symbol)
            report_sections.append({
                "title": f"Financial Analysis - {symbol}",
                "content": financial_data
            })
        
        # Section 3: Custom data aggregation
        custom_apis = await self._discover_relevant_apis(query)
        custom_data = await self._fetch_custom_data(custom_apis)
        if custom_data:
            report_sections.append({
                "title": "Additional Insights",
                "content": custom_data
            })
        
        # Generate final report
        report = self._format_report(query, report_sections)
        
        # Calculate ROI
        spending_status = self.client.get_spending_status()
        roi = self.total_value_obtained / max(spending_status["spent_today"], 0.01)
        
        print(f"\n💵 Report Generation Complete:")
        print(f"   Total spent: ${spending_status['spent_today']:.2f}")
        print(f"   Value obtained: ${self.total_value_obtained:.2f}")
        print(f"   ROI: {roi:.1f}x")
        print("="*60)
        
        return report
    
    def _aggregate_weather_data(self, results: List[Dict]) -> Dict[str, Any]:
        """Aggregate weather data from multiple sources"""
        
        temps = []
        conditions = []
        
        for result in results:
            data = result["data"]
            if "temperature" in data:
                temps.append(data["temperature"])
            if "conditions" in data:
                conditions.append(data["conditions"])
        
        return {
            "average_temperature": sum(temps) / len(temps) if temps else None,
            "conditions": max(set(conditions), key=conditions.count) if conditions else "Unknown",
            "sources": len(results),
            "confidence": min(0.95, len(results) * 0.3),
            "total_cost": sum(r["cost"] for r in results)
        }
    
    def _analyze_financial_data(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze aggregated financial data"""
        
        signals = []
        
        if "Technical Analysis API" in insights:
            ta_data = insights["Technical Analysis API"]
            if ta_data.get("rsi", 50) < 30:
                signals.append("oversold")
            elif ta_data.get("rsi", 50) > 70:
                signals.append("overbought")
        
        if "Sentiment Analysis API" in insights:
            sentiment = insights["Sentiment Analysis API"]
            if sentiment.get("score", 0) > 0.7:
                signals.append("positive_sentiment")
            elif sentiment.get("score", 0) < -0.7:
                signals.append("negative_sentiment")
        
        if "ML Predictions API" in insights:
            ml_pred = insights["ML Predictions API"]
            if ml_pred.get("direction", "") == "up":
                signals.append("bullish_forecast")
            elif ml_pred.get("direction", "") == "down":
                signals.append("bearish_forecast")
        
        # Determine overall recommendation
        bullish_signals = sum(1 for s in signals if s in ["oversold", "positive_sentiment", "bullish_forecast"])
        bearish_signals = sum(1 for s in signals if s in ["overbought", "negative_sentiment", "bearish_forecast"])
        
        if bullish_signals > bearish_signals:
            recommendation = "BUY"
        elif bearish_signals > bullish_signals:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        
        return {
            "signals": signals,
            "recommendation": recommendation,
            "confidence": len(insights) / 3.0  # Based on how many sources we got
        }
    
    async def _discover_relevant_apis(self, query: str) -> List[Dict[str, Any]]:
        """Discover APIs relevant to the query"""
        
        # In production, this would query an API marketplace
        # For demo, return mock APIs based on keywords
        
        apis = []
        
        if "news" in query.lower():
            apis.append({
                "name": "Premium News API",
                "url": "https://news.x402premium.com/latest",
                "max_amount": 0.05
            })
        
        if "social" in query.lower():
            apis.append({
                "name": "Social Sentiment API",
                "url": "https://social.sentiment.x402.com/trending",
                "max_amount": 0.03
            })
        
        return apis
    
    async def _fetch_custom_data(self, apis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fetch data from custom APIs"""
        
        if not apis:
            return {}
        
        results = {}
        
        for api in apis:
            try:
                result = await self.client.fetch_with_payment(
                    url=api["url"],
                    max_amount=api["max_amount"]
                )
                
                if result.success:
                    results[api["name"]] = result.data
                    
            except Exception as e:
                print(f"   ❌ Failed to fetch from {api['name']}: {e}")
        
        return results
    
    def _format_report(self, query: str, sections: List[Dict[str, Any]]) -> str:
        """Format the final report"""
        
        report = f"# Comprehensive Report\n\n"
        report += f"**Query**: {query}\n"
        report += f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        for section in sections:
            report += f"## {section['title']}\n\n"
            
            # Format content based on type
            content = section['content']
            if isinstance(content, dict):
                for key, value in content.items():
                    if isinstance(value, dict):
                        report += f"**{key}**:\n"
                        for k, v in value.items():
                            report += f"  - {k}: {v}\n"
                    else:
                        report += f"- **{key}**: {value}\n"
            else:
                report += f"{content}\n"
            
            report += "\n"
        
        report += f"\n---\n*Report generated using x402 payment protocol*"
        
        return report


async def main():
    """Run the API aggregator demonstration"""
    
    private_key = os.getenv("AGENT_PRIVATE_KEY", "0x" + "1" * 64)
    
    # Create aggregator agent
    agent = APIAggregatorAgent(private_key)
    
    # Example queries
    queries = [
        "What's the weather forecast and how is AAPL stock doing?",
        "Give me comprehensive financial analysis for TSLA",
        "Latest news and social sentiment analysis",
    ]
    
    for query in queries:
        report = await agent.create_comprehensive_report(query)
        
        print("\n" + "="*60)
        print("FINAL REPORT:")
        print("="*60)
        print(report)
        print("="*60 + "\n")
        
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())