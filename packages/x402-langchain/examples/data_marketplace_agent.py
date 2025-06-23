"""Example of an AI agent that purchases data from multiple sources"""

import os
from typing import List
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from x402_langchain import X402Agent, X402Config, create_x402_tool


class DataMarketplaceAgent:
    """Agent that can purchase data from various marketplaces"""
    
    def __init__(self, private_key: str):
        self.config = X402Config(
            private_key=private_key,
            spending_limits={
                "per_request": 5.0,  # $5 max per data purchase
                "per_hour": 20.0,
                "per_day": 100.0,
            },
            auto_approve=False,  # Manual approval for demo
            allowed_domains=[
                "data.bloomberg.example.com",
                "api.chainlink.example.com",
                "weather.noaa.example.com",
                "satellite.maxar.example.com",
            ]
        )
        
        # Custom approval logic
        self.config.approval_callback = self.approve_payment
        
        # Create tools
        self.payment_tool = create_x402_tool(
            private_key=private_key,
            spending_limit_daily=100.0,
            spending_limit_per_request=5.0,
            approval_callback=self.approve_payment
        )
        
        # Create analysis tools
        self.analysis_tools = self.create_analysis_tools()
        
        # Create LLM
        self.llm = ChatOpenAI(temperature=0, model="gpt-4")
    
    def approve_payment(self, url: str, amount: float) -> bool:
        """Custom approval logic for payments"""
        print(f"\n💳 Payment Approval Request:")
        print(f"   URL: {url}")
        print(f"   Amount: ${amount:.2f}")
        
        # Auto-approve small amounts
        if amount <= 0.10:
            print("   ✅ Auto-approved (small amount)")
            return True
        
        # Check if it's a trusted source
        trusted_sources = ["bloomberg", "chainlink", "noaa"]
        if any(source in url for source in trusted_sources):
            print("   ✅ Approved (trusted source)")
            return True
        
        # Manual approval for others
        response = input("   Approve? (y/n): ")
        return response.lower() == 'y'
    
    def create_analysis_tools(self) -> List[Tool]:
        """Create data analysis tools"""
        
        def analyze_market_data(data: str) -> str:
            """Analyze market data and provide insights"""
            # Simplified analysis
            return f"Market Analysis: The data shows positive trends with key indicators..."
        
        def compare_sources(source1: str, source2: str) -> str:
            """Compare data from two sources"""
            return f"Comparison: Source 1 and Source 2 show 95% correlation..."
        
        def generate_report(data: str) -> str:
            """Generate a summary report from data"""
            return f"Report: Based on the data, here are the key findings..."
        
        return [
            Tool(name="analyze_market", func=analyze_market_data, 
                 description="Analyze market data"),
            Tool(name="compare_sources", func=compare_sources,
                 description="Compare data from two sources"),
            Tool(name="generate_report", func=generate_report,
                 description="Generate summary report"),
        ]
    
    def research(self, topic: str) -> str:
        """Research a topic by purchasing data from multiple sources"""
        
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain import hub
        
        # Get prompt
        prompt = hub.pull("hwchase17/react")
        
        # Create agent
        tools = [self.payment_tool] + self.analysis_tools
        agent = create_react_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt
        )
        
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10
        )
        
        # Create research prompt
        research_prompt = f"""
        Research the topic: {topic}
        
        You have access to paid data sources. Use them wisely to gather information:
        1. Financial data: https://data.bloomberg.example.com/api/v1/search?q={topic}
        2. Oracle data: https://api.chainlink.example.com/data/topic/{topic}
        3. Weather data: https://weather.noaa.example.com/api/climate/{topic}
        4. Satellite imagery: https://satellite.maxar.example.com/imagery/location/{topic}
        
        Purchase relevant data, analyze it, and provide a comprehensive summary.
        Be mindful of costs - only purchase what's necessary.
        """
        
        return executor.run(research_prompt)


def main():
    # Get private key
    private_key = os.getenv("AGENT_PRIVATE_KEY", "0x...")
    
    # Create marketplace agent
    agent = DataMarketplaceAgent(private_key)
    
    # Research topics
    topics = [
        "corn futures midwest USA",
        "renewable energy investments 2024",
        "supply chain disruptions Asia",
    ]
    
    for topic in topics:
        print(f"\n{'='*80}")
        print(f"🔍 Researching: {topic}")
        print(f"{'='*80}")
        
        try:
            result = agent.research(topic)
            print(f"\n📊 Research Results:")
            print(result)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print(f"\n💰 Spending Summary:")
        # Note: Would need to access the internal client for spending report
        print(f"   Check agent logs for detailed spending")


if __name__ == "__main__":
    main()