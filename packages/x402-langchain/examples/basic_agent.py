"""Basic example of an AI agent that can make payments"""

import os
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain import hub

from x402_langchain import create_x402_agent, create_x402_tool

# Example: Create a simple agent that can pay for data
def main():
    # Get private key from environment
    private_key = os.getenv("AGENT_PRIVATE_KEY", "0x...")
    
    # Create LLM
    llm = ChatOpenAI(temperature=0, model="gpt-4")
    
    # Create x402 payment tool
    payment_tool = create_x402_tool(
        private_key=private_key,
        spending_limit_daily=10.0,  # $10 per day
        spending_limit_per_request=1.0,  # $1 per request
        auto_approve=True,
        allowed_domains=[
            "api.weather.example.com",
            "data.market.example.com",
            "inference.ai.example.com"
        ]
    )
    
    # Create other tools (example)
    def calculate(expression: str) -> str:
        """Calculate a mathematical expression"""
        try:
            result = eval(expression)
            return f"The result is: {result}"
        except:
            return "Invalid expression"
    
    calc_tool = Tool(
        name="calculator",
        func=calculate,
        description="Useful for mathematical calculations"
    )
    
    # Create agent with payment capabilities
    agent = create_x402_agent(
        private_key=private_key,
        llm=llm,
        tools=[payment_tool, calc_tool],
        spending_limit_daily=10.0,
        auto_approve=True,
        verbose=True
    )
    
    # Example queries
    queries = [
        "What's the current weather in New York? Use the API at https://api.weather.example.com/current?city=NYC",
        "Get me the latest Bitcoin price from https://data.market.example.com/crypto/BTC",
        "Calculate the ROI if Bitcoin goes from $50,000 to $75,000",
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        try:
            result = agent.run(query)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Show spending report
        report = agent.get_spending_report()
        print(f"\nSpending Report:")
        print(f"  Total spent today: ${report['spent_today']:.2f}")
        print(f"  Remaining today: ${report['remaining']['day']:.2f}")


if __name__ == "__main__":
    main()