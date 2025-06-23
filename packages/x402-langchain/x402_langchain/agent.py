"""High-level agent wrapper for x402 payments"""

from typing import Optional, List, Any, Dict
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import BaseLanguageModel

from .tools import X402PaymentTool, create_x402_tool
from .config import X402Config
from .client import X402Client


class X402Agent:
    """Wrapper for LangChain agents with x402 payment capabilities"""
    
    def __init__(
        self,
        base_agent: AgentExecutor,
        config: X402Config,
        additional_tools: Optional[List[BaseTool]] = None,
    ):
        self.config = config
        self.client = X402Client(config)
        self.payment_tool = X402PaymentTool(config)
        
        # Add payment tool to agent's tools
        all_tools = list(base_agent.tools)
        all_tools.append(self.payment_tool)
        if additional_tools:
            all_tools.extend(additional_tools)
        
        # Create new agent with payment capabilities
        self.agent = AgentExecutor(
            agent=base_agent.agent,
            tools=all_tools,
            verbose=base_agent.verbose,
            max_iterations=base_agent.max_iterations,
            max_execution_time=base_agent.max_execution_time,
            return_intermediate_steps=base_agent.return_intermediate_steps,
        )
    
    def run(self, *args, **kwargs) -> str:
        """Run the agent with payment capabilities"""
        return self.agent.run(*args, **kwargs)
    
    async def arun(self, *args, **kwargs) -> str:
        """Run the agent asynchronously"""
        return await self.agent.arun(*args, **kwargs)
    
    def get_spending_report(self) -> Dict[str, Any]:
        """Get a report of the agent's spending"""
        return self.client.get_spending_status()
    
    def invoke(self, *args, **kwargs):
        """Invoke the agent (compatible with newer LangChain versions)"""
        if hasattr(self.agent, 'invoke'):
            return self.agent.invoke(*args, **kwargs)
        else:
            return self.agent.run(*args, **kwargs)


def create_x402_agent(
    private_key: str,
    base_agent: Optional[AgentExecutor] = None,
    llm: Optional[BaseLanguageModel] = None,
    tools: Optional[List[BaseTool]] = None,
    spending_limit_daily: float = 100.0,
    auto_approve: bool = True,
    verbose: bool = False,
    **kwargs
) -> X402Agent:
    """Create an x402-enabled agent with simplified configuration"""
    
    # Create config
    config = X402Config(
        private_key=private_key,
        spending_limits={
            "per_request": kwargs.get("spending_limit_per_request", 1.0),
            "per_hour": spending_limit_daily / 24,
            "per_day": spending_limit_daily,
        },
        auto_approve=auto_approve,
        **{k: v for k, v in kwargs.items() if k in X402Config.__fields__}
    )
    
    # Create base agent if not provided
    if base_agent is None:
        if llm is None:
            raise ValueError("Either base_agent or llm must be provided")
        
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain import hub
        
        # Get a basic prompt
        prompt = hub.pull("hwchase17/react")
        
        # Create agent
        agent = create_react_agent(
            llm=llm,
            tools=tools or [],
            prompt=prompt,
        )
        
        base_agent = AgentExecutor(
            agent=agent,
            tools=tools or [],
            verbose=verbose,
        )
    
    return X402Agent(
        base_agent=base_agent,
        config=config,
        additional_tools=tools,
    )