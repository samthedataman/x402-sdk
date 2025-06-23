"""API mocking and simulation for x402 agents"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
import json
import random

from .models import PaymentResult
from .logger import logger


@dataclass
class MockAPI:
    """Configuration for a mocked API"""
    url: str
    cost: float
    response: Any
    latency: float = 0.1
    failure_rate: float = 0.0
    requires_auth: bool = False


class APIMockingEngine:
    """Engine for mocking x402-enabled APIs in development"""
    
    def __init__(self):
        self.mocked_apis: Dict[str, MockAPI] = {}
        self.call_history = []
        self.total_mock_spend = 0.0
        
    def mock_api(self, 
                 url_pattern: str,
                 response: Any,
                 cost: float = 0.01,
                 latency: float = 0.1,
                 failure_rate: float = 0.0):
        """Mock an API endpoint"""
        
        self.mocked_apis[url_pattern] = MockAPI(
            url=url_pattern,
            cost=cost,
            response=response,
            latency=latency,
            failure_rate=failure_rate,
        )
        
        logger.info(f"🎭 Mocked API: {url_pattern} (${cost})")
    
    def mock_common_apis(self):
        """Mock common API patterns for testing"""
        
        # Weather APIs
        self.mock_api(
            "weather.api/*",
            lambda city: {
                "city": city,
                "temperature": random.randint(60, 85),
                "conditions": random.choice(["Sunny", "Cloudy", "Rainy"]),
                "humidity": random.randint(40, 80),
            },
            cost=0.01
        )
        
        # Financial APIs
        self.mock_api(
            "finance.api/stock/*",
            lambda symbol: {
                "symbol": symbol,
                "price": round(random.uniform(100, 500), 2),
                "change": round(random.uniform(-5, 5), 2),
                "volume": random.randint(1000000, 10000000),
            },
            cost=0.05
        )
        
        # AI/ML APIs
        self.mock_api(
            "ml.api/predict",
            {
                "prediction": random.random(),
                "confidence": random.uniform(0.7, 0.95),
                "model_version": "v2.1",
            },
            cost=0.10
        )
        
        # News APIs
        self.mock_api(
            "news.api/latest",
            [
                {
                    "title": f"Breaking News {i}",
                    "summary": "Important developments in the market",
                    "timestamp": time.time() - (i * 3600),
                }
                for i in range(5)
            ],
            cost=0.02
        )
        
        logger.info("🎭 Loaded common API mocks")
    
    async def simulate_request(self, url: str) -> Optional[PaymentResult]:
        """Simulate an API request"""
        
        # Find matching mock
        mock = None
        for pattern, api in self.mocked_apis.items():
            if self._match_pattern(pattern, url):
                mock = api
                break
        
        if not mock:
            return None
        
        # Simulate latency
        await asyncio.sleep(mock.latency)
        
        # Simulate failures
        if random.random() < mock.failure_rate:
            logger.warning(f"🎭 Simulated failure for {url}")
            return PaymentResult(
                success=False,
                url=url,
                amount=str(mock.cost),
                error="Simulated API failure",
            )
        
        # Generate response
        if callable(mock.response):
            # Extract parameter from URL if needed
            parts = url.split("/")
            param = parts[-1] if parts else None
            response_data = mock.response(param)
        else:
            response_data = mock.response
        
        # Track the call
        self.call_history.append({
            "url": url,
            "cost": mock.cost,
            "timestamp": time.time(),
            "success": True,
        })
        
        self.total_mock_spend += mock.cost
        
        logger.debug(f"🎭 Mock response for {url}: ${mock.cost}")
        
        return PaymentResult(
            success=True,
            url=url,
            amount=str(mock.cost),
            token="MOCK",
            data=response_data,
        )
    
    def _match_pattern(self, pattern: str, url: str) -> bool:
        """Check if URL matches pattern"""
        
        if "*" in pattern:
            # Simple wildcard matching
            prefix = pattern.split("*")[0]
            return url.startswith(prefix)
        else:
            return pattern == url
    
    def get_mock_stats(self) -> Dict[str, Any]:
        """Get mocking statistics"""
        
        api_calls_by_url = {}
        for call in self.call_history:
            url = call["url"]
            if url not in api_calls_by_url:
                api_calls_by_url[url] = {"count": 0, "total_cost": 0.0}
            api_calls_by_url[url]["count"] += 1
            api_calls_by_url[url]["total_cost"] += call["cost"]
        
        return {
            "total_calls": len(self.call_history),
            "total_mock_spend": self.total_mock_spend,
            "mocked_apis": list(self.mocked_apis.keys()),
            "api_calls": api_calls_by_url,
            "average_cost": self.total_mock_spend / len(self.call_history) if self.call_history else 0,
        }
    
    def export_mock_data(self, filename: str = "mock_data.json"):
        """Export mock data for analysis"""
        
        data = {
            "stats": self.get_mock_stats(),
            "call_history": self.call_history,
            "mocked_apis": {
                pattern: {
                    "cost": api.cost,
                    "latency": api.latency,
                    "failure_rate": api.failure_rate,
                }
                for pattern, api in self.mocked_apis.items()
            }
        }
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"📊 Exported mock data to {filename}")


class CostDiscoveryTool:
    """Tool for discovering API costs before committing to payment"""
    
    def __init__(self):
        self.discovered_costs: Dict[str, float] = {}
        self.cost_history = []
        
    async def discover_cost(self, url: str) -> Optional[float]:
        """Discover the cost of an API without paying"""
        
        # Check cache first
        if url in self.discovered_costs:
            return self.discovered_costs[url]
        
        try:
            # Make OPTIONS request to discover cost
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.options(url, timeout=5.0)
                
                # Check for x402 payment requirement header
                if response.status_code == 402:
                    payment_data = response.json()
                    cost = float(payment_data.get("amount", 0))
                    
                    # Cache the cost
                    self.discovered_costs[url] = cost
                    self.cost_history.append({
                        "url": url,
                        "cost": cost,
                        "discovered_at": time.time(),
                    })
                    
                    logger.info(f"💰 Discovered cost for {url}: ${cost}")
                    return cost
                else:
                    # Free API
                    self.discovered_costs[url] = 0.0
                    return 0.0
                    
        except Exception as e:
            logger.warning(f"Failed to discover cost for {url}: {e}")
            return None
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of discovered costs"""
        
        total_apis = len(self.discovered_costs)
        free_apis = sum(1 for cost in self.discovered_costs.values() if cost == 0)
        paid_apis = total_apis - free_apis
        
        if paid_apis > 0:
            avg_cost = sum(cost for cost in self.discovered_costs.values() if cost > 0) / paid_apis
        else:
            avg_cost = 0
        
        return {
            "total_apis_discovered": total_apis,
            "free_apis": free_apis,
            "paid_apis": paid_apis,
            "average_cost": avg_cost,
            "most_expensive": max(self.discovered_costs.items(), key=lambda x: x[1]) if self.discovered_costs else None,
            "cheapest_paid": min((item for item in self.discovered_costs.items() if item[1] > 0), key=lambda x: x[1], default=None),
        }
    
    def find_alternatives(self, url: str, max_cost: float) -> List[Dict[str, Any]]:
        """Find alternative APIs within budget"""
        
        # Extract API type from URL
        api_type = self._extract_api_type(url)
        
        alternatives = []
        for api_url, cost in self.discovered_costs.items():
            if api_url != url and cost <= max_cost:
                if self._extract_api_type(api_url) == api_type:
                    alternatives.append({
                        "url": api_url,
                        "cost": cost,
                        "savings": self.discovered_costs.get(url, 0) - cost,
                    })
        
        return sorted(alternatives, key=lambda x: x["cost"])
    
    def _extract_api_type(self, url: str) -> str:
        """Extract API type from URL"""
        
        if "weather" in url.lower():
            return "weather"
        elif "finance" in url.lower() or "stock" in url.lower():
            return "finance"
        elif "news" in url.lower():
            return "news"
        elif "ml" in url.lower() or "predict" in url.lower():
            return "ml"
        else:
            return "general"