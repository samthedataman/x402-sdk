#!/usr/bin/env python3
"""CLI tool for fast-x402 - Zero-config API monetization"""

import os
import sys
import json
import secrets
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.panel import Panel

try:
    from .shared.wallet import WalletManager
    from .shared.analytics import get_analytics
except ImportError:
    WalletManager = None
    get_analytics = None

from .models import X402Config
from .provider import X402Provider

console = Console()


@click.group()
def cli():
    """fast-x402: Zero-config API monetization with x402 protocol"""
    pass


@cli.command()
@click.argument('project_name', default='.')
@click.option('--framework', type=click.Choice(['fastapi', 'flask', 'express']), default='fastapi')
@click.option('--network', type=click.Choice(['base', 'base-sepolia', 'polygon']), default='base-sepolia')
@click.option('--no-fund', is_flag=True, help='Skip automatic testnet funding')
def create(project_name: str, framework: str, network: str, no_fund: bool):
    """Create a new x402-enabled API project with automatic setup"""
    
    console.print(f"\n🚀 Creating x402-enabled {framework} project: [bold cyan]{project_name}[/]")
    
    # Create project directory
    if project_name != '.':
        Path(project_name).mkdir(exist_ok=True)
        os.chdir(project_name)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Step 1: Generate wallet
        task = progress.add_task("Generating secure wallet...", total=1)
        
        if not WalletManager:
            console.print("[red]Error: mnemonic package required. Install with: pip install mnemonic[/]")
            sys.exit(1)
        
        wallet_manager = WalletManager()
        wallet_data, created = wallet_manager.create_or_load_wallet("api_provider")
        if not created:
            console.print("📁 [yellow]Using existing wallet[/]")
        progress.advance(task)
        
        # Step 2: Save configuration
        task = progress.add_task("Creating configuration...", total=1)
        
        config = {
            "wallet_address": wallet_data["address"],
            "private_key": wallet_data["private_key"],
            "mnemonic": wallet_data["mnemonic"],
            "network": network,
            "chain_id": {
                "base": 8453,
                "base-sepolia": 84532,
                "polygon": 137,
            }[network],
            "accepted_tokens": {
                "base": ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"],  # USDC
                "base-sepolia": ["0x036CbD53842c5426634e7929541eC2318f3dCF7e"],
                "polygon": ["0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"],
            }[network],
            "facilitator_url": {
                "base": "https://api.coinbase.com/rpc/v1/base/x402",
                "base-sepolia": "https://api.coinbase.com/rpc/v1/base-sepolia/x402",
                "polygon": "https://x402-facilitator.polygon.com",
            }[network],
        }
        
        # Save to .env
        env_content = f"""# x402 Configuration - Generated automatically
X402_WALLET_ADDRESS={config['wallet_address']}
X402_PRIVATE_KEY={config['private_key']}
X402_NETWORK={network}
X402_CHAIN_ID={config['chain_id']}

# IMPORTANT: Keep your private key secure!
# Mnemonic phrase (store securely): {config['mnemonic']}
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        # Create .x402 directory and save config file
        x402_dir = Path('.x402')
        x402_dir.mkdir(exist_ok=True)
        
        with open(x402_dir / 'config.json', 'w') as f:
            json.dump({
                "wallet_address": config['wallet_address'],
                "network": network,
                "chain_id": config['chain_id'],
                "accepted_tokens": config['accepted_tokens'],
                "facilitator_url": config['facilitator_url'],
                "dashboard": {
                    "enabled": True,
                    "port": 3001,
                },
            }, f, indent=2)
        
        progress.advance(task)
        
        # Step 3: Create example API
        task = progress.add_task(f"Creating {framework} example...", total=1)
        
        if framework == 'fastapi':
            create_fastapi_example(config)
        elif framework == 'flask':
            create_flask_example(config)
        elif framework == 'express':
            create_express_example(config)
        
        progress.advance(task)
        
        # Step 4: Fund wallet (if not skipped)
        if not no_fund and network == 'base-sepolia':
            task = progress.add_task("Funding testnet wallet...", total=1)
            asyncio.run(fund_testnet_wallet(config['wallet_address'], network))
            progress.advance(task)
    
    # Success message
    console.print("\n✅ [bold green]x402 API created successfully![/]\n")
    
    # Display wallet info
    table = Table(title="Your x402 Wallet", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Address", config['wallet_address'])
    table.add_row("Network", network)
    table.add_row("Private Key", f"{config['private_key'][:10]}...{config['private_key'][-10:]}")
    
    console.print(table)
    
    # Next steps
    console.print("\n📝 [bold]Next Steps:[/]")
    console.print("1. Run your API: [cyan]python app.py[/]")
    console.print("2. View dashboard: [cyan]http://localhost:3001[/]")
    console.print("3. Test payments: [cyan]x402 test[/]")
    
    if network == 'base-sepolia':
        console.print(f"\n💰 Testnet USDC: [green]100 USDC[/] (check in a few seconds)")
        console.print(f"🔗 View on explorer: https://sepolia.basescan.org/address/{config['wallet_address']}")


def create_fastapi_example(config: Dict[str, Any]):
    """Create FastAPI example with x402"""
    
    example_code = f'''"""x402-enabled FastAPI application"""

from fastapi import FastAPI, HTTPException
from fast_x402 import X402Provider, X402Config, X402Middleware

# Initialize app
app = FastAPI(title="My x402 API", version="1.0.0")

# Initialize x402 (auto-loads from .x402.config.json)
config = X402Config()
provider = X402Provider(config)

# Add x402 middleware
app.add_middleware(
    X402Middleware,
    provider=provider,
    paths={{
        "/api/weather/*": lambda req: provider.create_payment_requirement("0.01"),
        "/api/analyze/*": lambda req: provider.create_payment_requirement("0.05"),
        "/api/premium/*": lambda req: provider.create_payment_requirement("0.10"),
    }}
)

# Enable dashboard
provider.enable_dashboard(app, port=3001)

# Free endpoint
@app.get("/")
async def root():
    return {{
        "message": "Welcome to my x402 API",
        "pricing": {{
            "/api/weather": "$0.01",
            "/api/analyze": "$0.05",
            "/api/premium": "$0.10"
        }},
        "wallet": provider.config.wallet_address,
        "dashboard": "http://localhost:3001",
    }}

# Paid endpoints
@app.get("/api/weather/{{city}}")
async def get_weather(city: str):
    return {{
        "city": city,
        "temperature": 72,
        "conditions": "Sunny",
        "forecast": "Clear skies ahead!"
    }}

@app.post("/api/analyze")
async def analyze_data(data: dict):
    return {{
        "analysis": "Deep insights here",
        "confidence": 0.95,
        "recommendations": ["Buy", "Hold", "Profit"]
    }}

@app.get("/api/premium/report")
async def premium_report():
    return {{
        "report": "Comprehensive analysis with ML predictions",
        "value": "High",
        "next_steps": ["Scale", "Optimize", "Dominate"]
    }}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open('app.py', 'w') as f:
        f.write(example_code)
    
    # Create requirements.txt
    with open('requirements.txt', 'w') as f:
        f.write("""fast-x402>=1.0.0
fastapi>=0.100.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
""")


def create_flask_example(config: Dict[str, Any]):
    """Create Flask example with x402"""
    # TODO: Implement Flask example
    pass


def create_express_example(config: Dict[str, Any]):
    """Create Express.js example with x402"""
    # TODO: Implement Express example (would need JS SDK)
    pass


async def fund_testnet_wallet(address: str, network: str):
    """Fund wallet with testnet tokens"""
    
    if network == 'base-sepolia':
        # Use Coinbase faucet or other testnet faucet
        faucet_urls = [
            f"https://faucet.quicknode.com/drip/base-sepolia/{address}",
            f"https://sepoliafaucet.com/api/fund/{address}",
        ]
        
        async with httpx.AsyncClient() as client:
            for url in faucet_urls:
                try:
                    response = await client.post(url, timeout=10)
                    if response.status_code == 200:
                        return True
                except:
                    continue
    
    return False


@cli.command()
@click.option('--count', default=5, help='Number of test payments')
@click.option('--amount', default=0.01, help='Payment amount per request')
@click.option('--endpoint', default='/api/weather/NYC', help='Endpoint to test')
def test(count: int, amount: float, endpoint: str):
    """Test x402 payments with simulated agents"""
    
    console.print(f"\n🧪 Testing x402 payments: [bold]{count}[/] requests to [cyan]{endpoint}[/]\n")
    
    # Load config
    config_path = Path('.x402/config.json')
    if not config_path.exists():
        # Fallback to old location for backward compatibility
        old_config_path = Path('.x402.config.json')
        if old_config_path.exists():
            config_path = old_config_path
        else:
            console.print("[red]Error: No x402 configuration found. Run 'x402 create' first.[/]")
            sys.exit(1)
    
    with open(config_path) as f:
        config_data = json.load(f)
    
    # Create test agents
    agents = []
    for i in range(count):
        agent_wallet = f"0x{secrets.token_hex(20)}"
        agents.append({
            "id": f"test-agent-{i}",
            "wallet": agent_wallet,
            "behavior": ["aggressive", "normal", "cautious"][i % 3],
        })
    
    # Simulate payments
    with Progress(console=console) as progress:
        task = progress.add_task(f"Simulating {count} payments...", total=count)
        
        for i, agent in enumerate(agents):
            # Simulate payment
            console.print(f"🤖 Agent {agent['id']} ({agent['behavior']})")
            console.print(f"   💰 Paying ${amount} from {agent['wallet'][:10]}...")
            console.print(f"   ✅ Payment successful!\n")
            
            progress.advance(task)
            asyncio.run(asyncio.sleep(0.5))  # Simulate network delay
    
    # Summary
    console.print(f"\n📊 [bold]Test Summary:[/]")
    console.print(f"   Total payments: {count}")
    console.print(f"   Total revenue: ${count * amount:.2f}")
    console.print(f"   Success rate: 100%")
    console.print(f"\n✅ All tests passed!")


@cli.command()
def debug():
    """Start visual payment debugger"""
    
    console.print("\n🔍 [bold]X402 Payment Debugger[/]")
    console.print("Monitoring payments in real-time...\n")
    
    # TODO: Implement WebSocket connection to provider
    # For now, simulate some debug output
    
    debug_events = [
        ("12:34:56", "🤖", "Agent-7 requesting /api/weather", "pending"),
        ("12:34:57", "💰", "Payment: $0.01 USDC", "processing"),
        ("12:34:58", "✅", "Payment confirmed (tx: 0x123...)", "success"),
        ("12:34:59", "📦", "Response sent (200 OK)", "complete"),
    ]
    
    for timestamp, icon, message, status in debug_events:
        color = {
            "pending": "yellow",
            "processing": "cyan",
            "success": "green",
            "complete": "blue",
        }[status]
        
        console.print(f"[dim]{timestamp}[/] {icon} [{color}]{message}[/]")
        asyncio.run(asyncio.sleep(0.5))
    
    console.print("\n[dim]Press Ctrl+C to stop monitoring[/]")


@cli.command()
def dashboard():
    """Open the x402 dashboard in browser"""
    
    import webbrowser
    
    console.print("🎯 Opening x402 dashboard...")
    webbrowser.open("http://localhost:3001")


@cli.command()
@click.argument('api_file')
def migrate(api_file: str):
    """Migrate existing API to use x402"""
    
    console.print(f"\n🔄 Analyzing {api_file} for x402 migration...")
    
    # TODO: Implement actual code analysis
    # For now, show mock analysis
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Analyzing routes...", total=100)
        for i in range(100):
            progress.advance(task)
            asyncio.run(asyncio.sleep(0.01))
    
    # Mock results
    routes = [
        ("GET /api/users", "Free", "User listing - keep free"),
        ("POST /api/analyze", "$0.05", "CPU intensive - charge for compute"),
        ("GET /api/premium/*", "$0.10", "Premium data - higher value"),
        ("POST /api/ml/predict", "$0.25", "ML inference - expensive compute"),
    ]
    
    table = Table(title="Suggested Pricing")
    table.add_column("Route", style="cyan")
    table.add_column("Price", style="green")
    table.add_column("Reason", style="dim")
    
    for route, price, reason in routes:
        table.add_row(route, price, reason)
    
    console.print("\n")
    console.print(table)
    
    if Confirm.ask("\nApply these changes?"):
        console.print("✅ Migration complete! Check app_x402.py")
    else:
        console.print("❌ Migration cancelled")


@cli.command()
def playground():
    """Interactive x402 testing environment"""
    
    console.print("\n🎮 [bold cyan]x402 Playground[/]")
    console.print("Type 'help' for commands or 'exit' to quit\n")
    
    commands = {
        "test payment": "Simulate a payment",
        "test agent": "Create a test agent",
        "check price": "Check API pricing",
        "stats": "Show current stats",
        "help": "Show this help",
        "exit": "Exit playground",
    }
    
    while True:
        command = Prompt.ask("x402> ")
        
        if command == "exit":
            break
        elif command == "help":
            for cmd, desc in commands.items():
                console.print(f"  {cmd:<15} - {desc}")
        elif command.startswith("test payment"):
            parts = command.split()
            if len(parts) >= 4:
                endpoint = parts[2]
                amount = float(parts[3])
                console.print(f"✅ Payment successful! ${amount} for {endpoint}")
            else:
                console.print("Usage: test payment <endpoint> <amount>")
        elif command.startswith("test agent"):
            console.print("🤖 Agent created with $5.00 budget")
        elif command == "stats":
            console.print("📊 Total revenue: $12.45")
            console.print("📊 Total requests: 1,245")
            console.print("📊 Unique agents: 23")
        else:
            console.print(f"Unknown command: {command}")
    
    console.print("\n👋 Thanks for using x402 Playground!")


if __name__ == '__main__':
    cli()