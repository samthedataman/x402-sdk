"""Development mode for x402 - Local testing without blockchain"""

import asyncio
import secrets
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from collections import defaultdict
import json

from .models import PaymentData, PaymentVerification, PaymentRequirement
from .logger import logger


class MockBlockchain:
    """Simulated blockchain for development"""
    
    def __init__(self):
        self.balances = defaultdict(lambda: 1000.0)  # Everyone starts with $1000
        self.transactions = []
        self.confirmations = {}
        
    async def get_balance(self, address: str, token: str = "USDC") -> float:
        """Get mock balance"""
        return self.balances[f"{address}:{token}"]
    
    async def transfer(self, from_addr: str, to_addr: str, amount: float, token: str = "USDC") -> str:
        """Simulate a transfer"""
        key = f"{from_addr}:{token}"
        
        if self.balances[key] < amount:
            raise ValueError("Insufficient balance")
        
        # Simulate transfer
        self.balances[key] -= amount
        self.balances[f"{to_addr}:{token}"] += amount
        
        # Create transaction
        tx_hash = f"0x{secrets.token_hex(32)}"
        self.transactions.append({
            "hash": tx_hash,
            "from": from_addr,
            "to": to_addr,
            "amount": amount,
            "token": token,
            "timestamp": time.time(),
            "block": len(self.transactions) + 1,
        })
        
        return tx_hash
    
    async def wait_for_confirmation(self, tx_hash: str, confirmations: int = 1) -> bool:
        """Simulate waiting for confirmations"""
        await asyncio.sleep(0.1 * confirmations)  # 100ms per confirmation
        self.confirmations[tx_hash] = confirmations
        return True
    
    def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction details"""
        for tx in self.transactions:
            if tx["hash"] == tx_hash:
                return tx
        return None


class MockFacilitator:
    """Simulated facilitator service for development"""
    
    def __init__(self, blockchain: MockBlockchain):
        self.blockchain = blockchain
        self.payment_requests = {}
        
    async def submit_payment(self, payment_data: PaymentData) -> str:
        """Process a mock payment"""
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Create payment ID
        payment_id = f"pay_{secrets.token_hex(16)}"
        
        # Store payment request
        self.payment_requests[payment_id] = {
            "data": payment_data,
            "status": "pending",
            "created_at": time.time(),
        }
        
        # Process payment in background
        asyncio.create_task(self._process_payment(payment_id))
        
        return payment_id
    
    async def _process_payment(self, payment_id: str):
        """Simulate payment processing"""
        
        request = self.payment_requests[payment_id]
        payment_data = request["data"]
        
        try:
            # Simulate blockchain transfer
            tx_hash = await self.blockchain.transfer(
                payment_data.from_address,
                payment_data.to,
                float(payment_data.value) / 1e6,  # Convert from token units
                payment_data.token
            )
            
            # Wait for confirmation
            await self.blockchain.wait_for_confirmation(tx_hash)
            
            # Update status
            request["status"] = "completed"
            request["tx_hash"] = tx_hash
            
        except Exception as e:
            request["status"] = "failed"
            request["error"] = str(e)
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status"""
        
        request = self.payment_requests.get(payment_id)
        if not request:
            return {"status": "not_found"}
        
        return {
            "payment_id": payment_id,
            "status": request["status"],
            "tx_hash": request.get("tx_hash"),
            "error": request.get("error"),
        }


class DevelopmentMode:
    """Development mode for local testing"""
    
    def __init__(self):
        self.blockchain = MockBlockchain()
        self.facilitator = MockFacilitator(self.blockchain)
        self.test_agents = {}
        self.api_responses = {}
        self.payment_log = []
        
        logger.info("🚀 Development mode activated - Using mock blockchain")
        
    def create_test_agent(self, name: str = None, balance: float = 100.0) -> Dict[str, Any]:
        """Create a test agent with funds"""
        
        agent_id = name or f"agent-{len(self.test_agents)}"
        wallet_address = f"0x{secrets.token_hex(20)}"
        
        # Fund the agent
        self.blockchain.balances[f"{wallet_address}:USDC"] = balance
        
        agent = {
            "id": agent_id,
            "wallet_address": wallet_address,
            "balance": balance,
            "created_at": time.time(),
            "payments": [],
        }
        
        self.test_agents[agent_id] = agent
        
        logger.info(f"🤖 Created test agent: {agent_id} with ${balance}")
        
        return agent
    
    def set_api_response(self, endpoint: str, response: Any, cost: float = 0.01):
        """Set mock response for an API endpoint"""
        
        self.api_responses[endpoint] = {
            "response": response,
            "cost": cost,
        }
        
        logger.debug(f"📡 Mocked API: {endpoint} (${cost})")
    
    async def simulate_payment(self, 
                             from_agent: str,
                             to_provider: str,
                             amount: float,
                             endpoint: str) -> Dict[str, Any]:
        """Simulate a complete payment flow"""
        
        agent = self.test_agents.get(from_agent)
        if not agent:
            raise ValueError(f"Unknown agent: {from_agent}")
        
        # Create payment data
        payment_data = PaymentData(
            from_address=agent["wallet_address"],
            to=to_provider,
            value=str(int(amount * 1e6)),  # Convert to token units
            token="0x0000000000000000000000000000000000000001",  # Mock USDC
            chain_id=31337,  # Local chain
            nonce="0x" + secrets.token_hex(32),
            valid_before=int(time.time()) + 300,
            signature="0x" + secrets.token_hex(65),  # Mock signature
        )
        
        # Submit to facilitator
        payment_id = await self.facilitator.submit_payment(payment_data)
        
        # Wait for completion
        max_attempts = 20
        for _ in range(max_attempts):
            status = await self.facilitator.get_payment_status(payment_id)
            if status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)
        
        # Log payment
        payment_log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": from_agent,
            "provider": to_provider,
            "amount": amount,
            "endpoint": endpoint,
            "status": status["status"],
            "tx_hash": status.get("tx_hash"),
        }
        
        self.payment_log.append(payment_log_entry)
        agent["payments"].append(payment_log_entry)
        
        logger.info(f"💰 Payment {status['status']}: {from_agent} → ${amount} → {endpoint}")
        
        return {
            "success": status["status"] == "completed",
            "payment_id": payment_id,
            "tx_hash": status.get("tx_hash"),
            "response": self.api_responses.get(endpoint, {}).get("response"),
        }
    
    async def simulate_payment_flow(self, payment_requirement: PaymentRequirement) -> PaymentVerification:
        """Simulate the complete payment verification flow"""
        
        # Always succeed in development mode
        logger.debug(f"🎮 Simulating payment: ${payment_requirement.amount} to {payment_requirement.recipient[:10]}...")
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Return successful verification
        return PaymentVerification(
            valid=True,
            transaction_hash=f"0x{secrets.token_hex(32)}",
        )
    
    def get_test_stats(self) -> Dict[str, Any]:
        """Get development mode statistics"""
        
        total_payments = len(self.payment_log)
        total_revenue = sum(p["amount"] for p in self.payment_log)
        
        agent_stats = {}
        for agent_id, agent in self.test_agents.items():
            agent_stats[agent_id] = {
                "balance": self.blockchain.balances[f"{agent['wallet_address']}:USDC"],
                "spent": sum(p["amount"] for p in agent["payments"]),
                "payments": len(agent["payments"]),
            }
        
        return {
            "mode": "development",
            "total_payments": total_payments,
            "total_revenue": total_revenue,
            "test_agents": len(self.test_agents),
            "agent_stats": agent_stats,
            "mocked_apis": list(self.api_responses.keys()),
            "blockchain_blocks": len(self.blockchain.transactions),
        }
    
    def replay_payment_history(self) -> List[Dict[str, Any]]:
        """Replay payment history for testing"""
        
        return self.payment_log
    
    def export_test_data(self, filename: str = "test_data.json"):
        """Export test data for analysis"""
        
        data = {
            "stats": self.get_test_stats(),
            "payment_log": self.payment_log,
            "agents": {
                agent_id: {
                    "wallet": agent["wallet_address"],
                    "balance": self.blockchain.balances[f"{agent['wallet_address']}:USDC"],
                    "payments": agent["payments"],
                }
                for agent_id, agent in self.test_agents.items()
            },
            "transactions": self.blockchain.transactions,
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"📊 Exported test data to {filename}")


class TestScenarios:
    """Pre-built test scenarios for development"""
    
    def __init__(self, dev_mode: DevelopmentMode):
        self.dev = dev_mode
        
    async def aggressive_agent(self, provider_address: str):
        """Simulate an aggressive agent making many requests"""
        
        agent = self.dev.create_test_agent("aggressive-agent", balance=50.0)
        
        endpoints = ["/api/weather", "/api/analyze", "/api/premium"]
        
        for i in range(20):
            endpoint = endpoints[i % len(endpoints)]
            cost = [0.01, 0.05, 0.10][i % 3]
            
            await self.dev.simulate_payment(
                agent["id"],
                provider_address,
                cost,
                endpoint
            )
            
            await asyncio.sleep(0.5)
    
    async def budget_conscious_agent(self, provider_address: str):
        """Simulate a budget-conscious agent"""
        
        agent = self.dev.create_test_agent("budget-agent", balance=10.0)
        
        # Only use cheap endpoints
        for i in range(10):
            await self.dev.simulate_payment(
                agent["id"],
                provider_address,
                0.01,
                "/api/weather"
            )
            
            await asyncio.sleep(2.0)  # Slower pace
    
    async def failing_payments(self, provider_address: str):
        """Simulate failing payments"""
        
        agent = self.dev.create_test_agent("poor-agent", balance=0.5)
        
        # Try expensive endpoints with insufficient funds
        for i in range(5):
            try:
                await self.dev.simulate_payment(
                    agent["id"],
                    provider_address,
                    1.00,  # Too expensive
                    "/api/premium"
                )
            except Exception as e:
                logger.warning(f"❌ Payment failed as expected: {e}")
            
            await asyncio.sleep(1.0)