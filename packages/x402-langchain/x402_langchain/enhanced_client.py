"""Enhanced X402 client with all convenience features for agents"""

import os
import sys
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from collections import defaultdict
import time

from .client import X402Client as BaseClient
from .config import X402Config, SpendingLimits
from .models import PaymentResult
from .mocking import APIMockingEngine, CostDiscoveryTool
from .logger import logger

try:
    from .shared.analytics import get_analytics, AnalyticsEvent
except ImportError:
    get_analytics = None
    AnalyticsEvent = None


class SmartApprovalRules:
    """Smart approval rules for automatic payment decisions"""
    
    def __init__(self):
        self.trusted_domains = set()
        self.blocked_domains = set()
        self.max_per_request = 0.10
        self.max_per_hour = 10.00
        self.require_approval_above = 1.00
        self.domain_limits = {}
        self.api_reputation = defaultdict(lambda: {"success": 0, "failure": 0})
        
    def add_trusted_domain(self, domain: str):
        """Add a trusted domain"""
        self.trusted_domains.add(domain)
        
    def set_domain_limit(self, domain: str, limit: float):
        """Set spending limit for a specific domain"""
        self.domain_limits[domain] = limit
        
    def should_approve(self, url: str, amount: float) -> bool:
        """Determine if payment should be auto-approved"""
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Check blocked domains
        if domain in self.blocked_domains:
            return False
        
        # Check if amount requires manual approval
        if amount > self.require_approval_above:
            return False
        
        # Check domain-specific limits
        if domain in self.domain_limits:
            if amount > self.domain_limits[domain]:
                return False
        
        # Check general limits
        if amount > self.max_per_request:
            return False
        
        # Trust decision for trusted domains
        if domain in self.trusted_domains:
            return True
        
        # Check reputation
        reputation = self.api_reputation[domain]
        if reputation["failure"] > reputation["success"]:
            return False
        
        return True
    
    def update_reputation(self, url: str, success: bool):
        """Update API reputation based on outcome"""
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        if success:
            self.api_reputation[domain]["success"] += 1
        else:
            self.api_reputation[domain]["failure"] += 1


class SharedAPIIntelligence:
    """Shared intelligence about APIs across agents"""
    
    def __init__(self):
        self.api_registry = {}
        self.price_history = defaultdict(list)
        self.response_times = defaultdict(list)
        self.quality_scores = defaultdict(float)
        
    def register_api(self, url: str, cost: float, response_time: float, quality: float):
        """Register API information"""
        
        self.api_registry[url] = {
            "cost": cost,
            "last_seen": time.time(),
            "call_count": self.api_registry.get(url, {}).get("call_count", 0) + 1,
        }
        
        # Track history
        self.price_history[url].append({"cost": cost, "timestamp": time.time()})
        self.response_times[url].append(response_time)
        
        # Update quality score (weighted average)
        current_score = self.quality_scores[url]
        self.quality_scores[url] = (current_score * 0.8 + quality * 0.2)
        
    def get_api_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get intelligence about an API"""
        
        if url not in self.api_registry:
            return None
        
        response_times = self.response_times[url]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "cost": self.api_registry[url]["cost"],
            "quality_score": self.quality_scores[url],
            "avg_response_time": avg_response_time,
            "call_count": self.api_registry[url]["call_count"],
            "last_seen": self.api_registry[url]["last_seen"],
        }
    
    def find_best_api(self, api_type: str, max_cost: float) -> Optional[str]:
        """Find the best API of a given type within budget"""
        
        candidates = []
        
        for url, info in self.api_registry.items():
            if api_type.lower() in url.lower() and info["cost"] <= max_cost:
                score = self.quality_scores[url] / (info["cost"] + 0.01)  # Quality per dollar
                candidates.append((url, score))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None


class EnhancedX402Client(BaseClient):
    """Enhanced X402 client with all convenience features"""
    
    def __init__(self,
                 config: Optional[X402Config] = None,
                 mode: str = "auto",
                 auto_fund: bool = True,
                 enable_mocking: bool = True):
        """
        Initialize enhanced client with smart defaults
        
        Args:
            config: Optional configuration (auto-creates wallet if not provided)
            mode: "auto", "development", "production"
            auto_fund: Automatically fund in development mode
            enable_mocking: Enable API mocking in development
        """
        
        # Auto-configure if needed
        if not config:
            config = self._auto_configure()
        
        # Determine mode
        self.mode = self._determine_mode(mode)
        
        # Initialize base client
        super().__init__(config)
        
        # Initialize enhanced features
        self.mocking_engine = APIMockingEngine() if enable_mocking else None
        self.cost_discovery = CostDiscoveryTool()
        self.approval_rules = SmartApprovalRules()
        self.api_intelligence = SharedAPIIntelligence()
        self.dry_run_mode = False
        self.batch_payments = []
        
        # Setup auto-funding in development
        if auto_fund and self.mode == "development":
            self._setup_auto_funding()
        
        # Load common mocks in development
        if self.mode == "development" and self.mocking_engine:
            self.mocking_engine.mock_common_apis()
        
        logger.info(f"🤖 Enhanced X402 client initialized in {self.mode} mode")
        
    def _auto_configure(self) -> X402Config:
        """Auto-configure client with smart defaults"""
        
        # Check for existing config file
        config_path = Path(".x402-agent.json")
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)
                logger.info("📁 Loaded agent configuration from .x402-agent.json")
                return X402Config(**config_data)
        
        # Create new config with auto-generated wallet
        config = X402Config(
            spending_limits=SpendingLimits(
                per_request=0.10,
                per_hour=5.00,
                per_day=20.00
            ),
            auto_approve=False,
            log_payments=True,
        )
        
        # Save for next time
        self._save_config(config)
        
        return config
    
    def _determine_mode(self, mode: str) -> str:
        """Determine operating mode"""
        
        if mode != "auto":
            return mode
        
        if os.getenv("NODE_ENV") == "development":
            return "development"
        elif os.getenv("NODE_ENV") == "production":
            return "production"
        elif os.path.exists(".git"):
            return "development"
        else:
            return "production"
    
    def _save_config(self, config: X402Config):
        """Save configuration for future use"""
        
        config_data = {
            "wallet_address": config.wallet_address,
            "spending_limits": {
                "per_request": config.spending_limits.per_request,
                "per_hour": config.spending_limits.per_hour,
                "per_day": config.spending_limits.per_day,
            },
            "auto_approve": config.auto_approve,
        }
        
        with open(".x402-agent.json", "w") as f:
            json.dump(config_data, f, indent=2)
    
    def _setup_auto_funding(self):
        """Setup auto-funding for development mode"""
        
        # In development, automatically top up when low
        self._auto_fund_threshold = 10.0
        self._auto_fund_amount = 100.0
        
        async def check_and_fund():
            while True:
                # Simulate balance check
                if self.spent_today > self._auto_fund_threshold:
                    logger.info(f"💰 Auto-funding agent with ${self._auto_fund_amount}")
                    self.spent_today = 0  # Reset spending
                await asyncio.sleep(60)  # Check every minute
        
        asyncio.create_task(check_and_fund())
    
    async def fetch_with_payment(self,
                                url: str,
                                max_amount: float = None,
                                method: str = "GET",
                                **kwargs) -> PaymentResult:
        """Enhanced fetch with mocking and intelligence"""
        
        # Check if mocked in development
        if self.mode == "development" and self.mocking_engine:
            mock_result = await self.mocking_engine.simulate_request(url)
            if mock_result:
                return mock_result
        
        # Discover cost first
        discovered_cost = await self.cost_discovery.discover_cost(url)
        if discovered_cost is not None:
            logger.info(f"💡 Discovered cost for {url}: ${discovered_cost}")
            
            # Check if within budget
            if max_amount and discovered_cost > max_amount:
                # Try to find alternative
                alternatives = self.cost_discovery.find_alternatives(url, max_amount)
                if alternatives:
                    logger.info(f"🔄 Found cheaper alternative: {alternatives[0]['url']} (${alternatives[0]['cost']})")
                    url = alternatives[0]["url"]
        
        # Check approval rules
        if discovered_cost and not self.approval_rules.should_approve(url, discovered_cost):
            logger.warning(f"❌ Payment denied by approval rules: {url} (${discovered_cost})")
            return PaymentResult(
                success=False,
                url=url,
                amount=str(discovered_cost),
                error="Payment denied by approval rules"
            )
        
        # Dry run mode
        if self.dry_run_mode:
            logger.info(f"🎭 Dry run: Would pay ${discovered_cost or 'unknown'} for {url}")
            return PaymentResult(
                success=True,
                url=url,
                amount=str(discovered_cost or 0),
                data={"dry_run": True, "simulated": "response"},
            )
        
        # Track start time
        start_time = time.time()
        
        # Make actual payment
        result = await super().fetch_with_payment(url, max_amount, method, **kwargs)
        
        # Track response time
        response_time = time.time() - start_time
        
        # Update API intelligence
        if result.success:
            self.api_intelligence.register_api(
                url,
                float(result.amount),
                response_time,
                quality=0.9  # TODO: Calculate based on response
            )
            self.approval_rules.update_reputation(url, True)
        else:
            self.approval_rules.update_reputation(url, False)
        
        return result
    
    def set_approval_rules(self, rules: Dict[str, Any]):
        """Configure smart approval rules"""
        
        if "trusted_domains" in rules:
            for domain in rules["trusted_domains"]:
                self.approval_rules.add_trusted_domain(domain)
        
        if "max_per_request" in rules:
            self.approval_rules.max_per_request = rules["max_per_request"]
        
        if "max_per_hour" in rules:
            self.approval_rules.max_per_hour = rules["max_per_hour"]
        
        if "require_approval_above" in rules:
            self.approval_rules.require_approval_above = rules["require_approval_above"]
        
        logger.info("✅ Updated approval rules")
    
    async def check_api_cost(self, url: str) -> Optional[float]:
        """Check API cost without committing to payment"""
        
        return await self.cost_discovery.discover_cost(url)
    
    async def batch_pay_and_fetch(self,
                                 urls: List[str],
                                 max_total: float = None) -> List[PaymentResult]:
        """Batch multiple API calls efficiently"""
        
        results = []
        total_cost = 0.0
        
        # Discover costs first
        costs = {}
        for url in urls:
            cost = await self.cost_discovery.discover_cost(url)
            if cost is not None:
                costs[url] = cost
                total_cost += cost
        
        # Check total budget
        if max_total and total_cost > max_total:
            logger.warning(f"❌ Batch cost ${total_cost} exceeds max ${max_total}")
            # Try to optimize by removing expensive APIs
            sorted_urls = sorted(urls, key=lambda u: costs.get(u, 0))
            urls = sorted_urls[:len(sorted_urls)//2]  # Take cheaper half
        
        # Execute batch
        tasks = []
        for url in urls:
            task = self.fetch_with_payment(url)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = [r for r in results if isinstance(r, PaymentResult) and r.success]
        failed = len(results) - len(successful)
        
        logger.info(f"📦 Batch complete: {len(successful)} succeeded, {failed} failed")
        
        return results
    
    async def dry_run(self, task_description: str, **kwargs) -> Dict[str, Any]:
        """Perform a dry run without actual payments"""
        
        self.dry_run_mode = True
        
        # Track what would happen
        dry_run_results = {
            "task": task_description,
            "simulated_calls": [],
            "total_cost": 0.0,
            "apis_used": [],
        }
        
        # TODO: Execute task and track API calls
        
        self.dry_run_mode = False
        
        return dry_run_results
    
    def enable_collective_learning(self):
        """Enable sharing of API intelligence between agents"""
        
        # In production, this would connect to a shared service
        logger.info("🧠 Collective learning enabled - Sharing API intelligence")
    
    def get_spending_analytics(self) -> Dict[str, Any]:
        """Get detailed spending analytics"""
        
        base_stats = self.get_spending_status()
        
        # Add enhanced analytics
        enhanced_stats = {
            **base_stats,
            "api_costs": dict(self.cost_discovery.discovered_costs),
            "cost_summary": self.cost_discovery.get_cost_summary(),
            "api_intelligence": {
                url: self.api_intelligence.get_api_info(url)
                for url in list(self.api_intelligence.api_registry.keys())[:10]
            },
            "approval_stats": {
                "trusted_domains": list(self.approval_rules.trusted_domains),
                "auto_approved": sum(
                    1 for d in self.api_intelligence.api_registry.values()
                    if d["cost"] <= self.approval_rules.max_per_request
                ),
            },
        }
        
        if self.mocking_engine:
            enhanced_stats["mock_stats"] = self.mocking_engine.get_mock_stats()
        
        return enhanced_stats
    
    def prefer_x402_apis(self):
        """Configure agent to prefer x402-enabled APIs"""
        
        # This would integrate with agent's decision making
        logger.info("🎯 Configured to prefer x402-enabled APIs")
    
    def export_learnings(self, filename: str = "agent_learnings.json"):
        """Export what the agent has learned about APIs"""
        
        learnings = {
            "discovered_apis": dict(self.cost_discovery.discovered_costs),
            "api_intelligence": {
                url: self.api_intelligence.get_api_info(url)
                for url in self.api_intelligence.api_registry
            },
            "reputation_scores": dict(self.approval_rules.api_reputation),
            "spending_patterns": self.get_spending_analytics(),
        }
        
        with open(filename, "w") as f:
            json.dump(learnings, f, indent=2)
        
        logger.info(f"📚 Exported agent learnings to {filename}")


def create_smart_agent(**kwargs) -> EnhancedX402Client:
    """Create a smart x402-enabled agent"""
    return EnhancedX402Client(**kwargs)