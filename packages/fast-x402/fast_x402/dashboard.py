"""Real-time dashboard for x402 providers"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import secrets

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn


class X402Dashboard:
    """Real-time payment monitoring dashboard"""
    
    def __init__(self, provider):
        self.provider = provider
        self.payment_history = deque(maxlen=100)  # Last 100 payments
        self.hourly_stats = defaultdict(lambda: {"count": 0, "revenue": 0.0})
        self.active_connections: List[WebSocket] = []
        self.start_time = time.time()
        
    async def track_payment(self, payment_data: Dict[str, Any]):
        """Track a payment in the dashboard"""
        
        # Convert amount to float if it's a string
        amount = payment_data.get("amount", 0)
        if isinstance(amount, str):
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0.0
        
        event = {
            "id": secrets.token_hex(8),
            "timestamp": datetime.utcnow().isoformat(),
            "from_address": payment_data.get("from_address", "Unknown"),
            "amount": amount,
            "token": payment_data.get("token", "USDC"),
            "endpoint": payment_data.get("endpoint", "/unknown"),
            "status": payment_data.get("status", "completed"),
            "tx_hash": payment_data.get("tx_hash", ""),
        }
        
        self.payment_history.append(event)
        
        # Update hourly stats
        hour_key = datetime.utcnow().strftime("%Y-%m-%d-%H")
        self.hourly_stats[hour_key]["count"] += 1
        self.hourly_stats[hour_key]["revenue"] += event["amount"]
        
        # Broadcast to all connected clients
        await self.broadcast({"type": "payment", "data": event})
        
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current dashboard statistics"""
        
        # Safely calculate total revenue, handling string amounts
        total_revenue = 0.0
        for p in self.payment_history:
            amount = p["amount"]
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0.0
            total_revenue += amount
        
        total_payments = len(self.payment_history)
        
        # Calculate revenue by hour for chart
        hourly_data = []
        for i in range(24):
            hour = datetime.utcnow() - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            stats = self.hourly_stats.get(hour_key, {"count": 0, "revenue": 0.0})
            hourly_data.append({
                "hour": hour.strftime("%H:00"),
                "revenue": stats["revenue"],
                "count": stats["count"],
            })
        
        # Get top payers
        payer_revenue = defaultdict(float)
        for payment in self.payment_history:
            amount = payment["amount"]
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0.0
            payer_revenue[payment["from_address"][:10]] += amount
        
        top_payers = sorted(
            payer_revenue.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Get endpoint breakdown
        endpoint_revenue = defaultdict(float)
        for payment in self.payment_history:
            amount = payment["amount"]
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0.0
            endpoint_revenue[payment["endpoint"]] += amount
        
        return {
            "total_revenue": total_revenue,
            "total_payments": total_payments,
            "average_payment": total_revenue / total_payments if total_payments > 0 else 0,
            "hourly_data": list(reversed(hourly_data)),
            "top_payers": [{"address": addr, "revenue": rev} for addr, rev in top_payers],
            "endpoint_breakdown": dict(endpoint_revenue),
            "uptime": time.time() - self.start_time,
            "wallet_address": self.provider.config.wallet_address,
            "network": getattr(self.provider.config, "network", "unknown"),
        }
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data compatible with the expected interface"""
        
        stats = self.get_stats()
        
        return {
            "total_payments": stats["total_payments"],
            "total_revenue": stats["total_revenue"],
            "average_payment": stats["average_payment"],
            "conversion_rate": 1.0 if stats["total_payments"] > 0 else 0.0,
            "top_payers": stats["top_payers"],
            "endpoint_breakdown": stats["endpoint_breakdown"],
            "hourly_data": stats["hourly_data"],
            "uptime_seconds": stats["uptime"],
            "wallet_address": stats["wallet_address"],
            "network": stats["network"],
        }
    
    def create_app(self, port: int = 3001) -> FastAPI:
        """Create the dashboard FastAPI app"""
        
        app = FastAPI(title="x402 Dashboard")
        
        @app.get("/")
        async def dashboard():
            """Serve the dashboard HTML"""
            return HTMLResponse(self.get_dashboard_html())
        
        @app.get("/api/stats")
        async def get_stats():
            """Get current statistics"""
            return self.get_stats()
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            # Send initial stats
            await websocket.send_json({
                "type": "stats",
                "data": self.get_stats()
            })
            
            try:
                while True:
                    # Keep connection alive
                    await asyncio.sleep(30)
                    await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
        
        @app.post("/api/test-payment")
        async def test_payment():
            """Generate a test payment for demo purposes"""
            test_payment = {
                "from_address": f"0x{secrets.token_hex(20)}",
                "amount": 0.01 + (secrets.randbelow(20) / 100),
                "token": "USDC",
                "endpoint": ["/api/weather", "/api/analyze", "/api/premium"][secrets.randbelow(3)],
                "status": "completed",
                "tx_hash": f"0x{secrets.token_hex(32)}",
            }
            
            await self.track_payment(test_payment)
            return {"success": True, "payment": test_payment}
        
        return app
    
    def get_dashboard_html(self) -> str:
        """Get the dashboard HTML page"""
        
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>x402 Payment Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #ffffff;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        h1 { 
            font-size: 2.5em;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .wallet-info {
            font-size: 0.9em;
            color: #888;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #00ff88;
            margin: 10px 0;
        }
        .stat-label {
            color: #888;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 1px;
        }
        .chart-container {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            height: 400px;
        }
        .payment-feed {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        .payment-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #333;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .payment-amount {
            color: #00ff88;
            font-weight: bold;
        }
        .payment-address {
            color: #888;
            font-family: monospace;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00ff88;
            margin-right: 10px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .test-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            color: #000;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .test-button:hover {
            transform: scale(1.05);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>x402 Payment Dashboard</h1>
        <div class="wallet-info">
            <div>Wallet: <span id="wallet-address">Loading...</span></div>
            <div>Network: <span id="network">Loading...</span></div>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Revenue</div>
            <div class="stat-value" id="total-revenue">$0.00</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Payments</div>
            <div class="stat-value" id="total-payments">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Average Payment</div>
            <div class="stat-value" id="average-payment">$0.00</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Live Status</div>
            <div class="stat-value"><span class="status-indicator"></span>Active</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="revenue-chart"></canvas>
    </div>
    
    <h2>Live Payment Feed</h2>
    <div class="payment-feed" id="payment-feed">
        <div style="text-align: center; color: #888; padding: 50px;">
            Waiting for payments...
        </div>
    </div>
    
    <button class="test-button" onclick="testPayment()">Test Payment</button>
    
    <script>
        let ws;
        let revenueChart;
        
        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'stats') {
                    updateStats(message.data);
                } else if (message.type === 'payment') {
                    addPayment(message.data);
                    updateRealtimeStats();
                }
            };
            
            ws.onclose = () => {
                setTimeout(connect, 3000);
            };
        }
        
        function updateStats(stats) {
            document.getElementById('wallet-address').textContent = 
                stats.wallet_address.substring(0, 6) + '...' + stats.wallet_address.substring(38);
            document.getElementById('network').textContent = stats.network;
            document.getElementById('total-revenue').textContent = `$${stats.total_revenue.toFixed(2)}`;
            document.getElementById('total-payments').textContent = stats.total_payments;
            document.getElementById('average-payment').textContent = `$${stats.average_payment.toFixed(2)}`;
            
            updateChart(stats.hourly_data);
        }
        
        function updateChart(hourlyData) {
            const ctx = document.getElementById('revenue-chart').getContext('2d');
            
            if (revenueChart) {
                revenueChart.destroy();
            }
            
            revenueChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: hourlyData.map(d => d.hour),
                    datasets: [{
                        label: 'Revenue',
                        data: hourlyData.map(d => d.revenue),
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: (value) => '$' + value.toFixed(2),
                                color: '#888'
                            },
                            grid: { color: '#333' }
                        },
                        x: {
                            ticks: { color: '#888' },
                            grid: { color: '#333' }
                        }
                    }
                }
            });
        }
        
        function addPayment(payment) {
            const feed = document.getElementById('payment-feed');
            
            if (feed.children[0]?.textContent?.includes('Waiting for payments')) {
                feed.innerHTML = '';
            }
            
            const item = document.createElement('div');
            item.className = 'payment-item';
            item.innerHTML = `
                <div>
                    <div class="payment-amount">$${(typeof payment.amount === 'string' ? parseFloat(payment.amount) : payment.amount).toFixed(2)} ${payment.token}</div>
                    <div class="payment-address">${payment.from_address.substring(0, 10)}...</div>
                </div>
                <div>
                    <div>${payment.endpoint}</div>
                    <div style="color: #888; font-size: 0.8em;">${new Date(payment.timestamp).toLocaleTimeString()}</div>
                </div>
            `;
            
            feed.insertBefore(item, feed.firstChild);
            
            if (feed.children.length > 20) {
                feed.removeChild(feed.lastChild);
            }
        }
        
        async function updateRealtimeStats() {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            updateStats(stats);
        }
        
        async function testPayment() {
            await fetch('/api/test-payment', { method: 'POST' });
        }
        
        // Initialize
        connect();
        updateRealtimeStats();
        setInterval(updateRealtimeStats, 10000);
    </script>
</body>
</html>'''


def enable_dashboard(provider, app: Optional[FastAPI] = None, port: int = 3001):
    """Enable the dashboard for a provider"""
    
    dashboard = X402Dashboard(provider)
    
    if app:
        # Mount dashboard to existing app
        dashboard_app = dashboard.create_app(port)
        app.mount("/x402-dashboard", dashboard_app)
        print(f"📊 x402 Dashboard enabled at: http://localhost:{port}/x402-dashboard")
    else:
        # Run standalone
        dashboard_app = dashboard.create_app(port)
        uvicorn.run(dashboard_app, host="0.0.0.0", port=port)
    
    return dashboard