"""Tests for X402Agent"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain.agents import AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from x402_langchain import X402Agent, create_x402_agent, X402Config
from x402_langchain.tools import X402PaymentTool


@pytest.fixture
def mock_llm():
    """Create mock LLM"""
    llm = Mock(spec=ChatOpenAI)
    llm.invoke = Mock(return_value="Test response")
    return llm


@pytest.fixture
def mock_base_agent(mock_llm):
    """Create mock base agent"""
    # Create a simple tool
    def dummy_tool(query: str) -> str:
        return f"Result for: {query}"
    
    tool = Tool(name="dummy", func=dummy_tool, description="Dummy tool")
    
    # Create mock agent executor
    agent_executor = Mock(spec=AgentExecutor)
    agent_executor.agent = Mock()
    agent_executor.tools = [tool]
    agent_executor.verbose = False
    agent_executor.max_iterations = 10
    agent_executor.max_execution_time = None
    agent_executor.return_intermediate_steps = False
    
    return agent_executor


@pytest.fixture
def config():
    """Create test configuration"""
    return X402Config(
        private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        spending_limits={
            "per_request": 1.0,
            "per_hour": 10.0,
            "per_day": 100.0,
        },
        auto_approve=True,
    )


class TestX402Agent:
    def test_agent_initialization(self, mock_base_agent, config):
        """Test agent initialization adds payment tool"""
        agent = X402Agent(mock_base_agent, config)
        
        # Check payment tool was added
        assert any(isinstance(tool, X402PaymentTool) for tool in agent.agent.tools)
        assert len(agent.agent.tools) == 2  # Original tool + payment tool
    
    def test_agent_with_additional_tools(self, mock_base_agent, config):
        """Test agent with additional tools"""
        extra_tool = Tool(
            name="extra",
            func=lambda x: f"Extra: {x}",
            description="Extra tool"
        )
        
        agent = X402Agent(mock_base_agent, config, additional_tools=[extra_tool])
        
        # Check all tools are present
        assert len(agent.agent.tools) == 3  # Original + payment + extra
        tool_names = [tool.name for tool in agent.agent.tools]
        assert "dummy" in tool_names
        assert "x402_payment" in tool_names
        assert "extra" in tool_names
    
    def test_agent_run(self, mock_base_agent, config):
        """Test agent run method"""
        agent = X402Agent(mock_base_agent, config)
        
        # Mock the run method
        agent.agent.run = Mock(return_value="Agent response")
        
        result = agent.run("Test query")
        
        assert result == "Agent response"
        agent.agent.run.assert_called_once_with("Test query")
    
    @pytest.mark.asyncio
    async def test_agent_arun(self, mock_base_agent, config):
        """Test agent async run method"""
        agent = X402Agent(mock_base_agent, config)
        
        # Mock the arun method
        agent.agent.arun = Mock(return_value="Async response")
        
        result = await agent.arun("Test query")
        
        assert result == "Async response"
        agent.agent.arun.assert_called_once_with("Test query")
    
    def test_agent_invoke_compatibility(self, mock_base_agent, config):
        """Test agent invoke method for newer LangChain versions"""
        agent = X402Agent(mock_base_agent, config)
        
        # Test when invoke exists
        agent.agent.invoke = Mock(return_value="Invoke response")
        result = agent.invoke("Test query")
        assert result == "Invoke response"
        
        # Test fallback to run when invoke doesn't exist
        delattr(agent.agent, "invoke")
        agent.agent.run = Mock(return_value="Run response")
        result = agent.invoke("Test query")
        assert result == "Run response"
    
    def test_spending_report(self, mock_base_agent, config):
        """Test getting spending report"""
        agent = X402Agent(mock_base_agent, config)
        
        # Mock client spending status
        mock_status = {
            "wallet_address": "0x123...",
            "spent_today": 5.50,
            "spent_hour": 1.25,
            "remaining": {"day": 94.50, "hour": 8.75},
        }
        agent.client.get_spending_status = Mock(return_value=mock_status)
        
        report = agent.get_spending_report()
        
        assert report == mock_status
        assert report["spent_today"] == 5.50


class TestCreateX402Agent:
    def test_create_agent_with_base_agent(self, mock_base_agent):
        """Test creating agent with existing base agent"""
        agent = create_x402_agent(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            base_agent=mock_base_agent,
            spending_limit_daily=50.0,
        )
        
        assert isinstance(agent, X402Agent)
        assert agent.config.spending_limits.per_day == 50.0
        assert any(isinstance(tool, X402PaymentTool) for tool in agent.agent.tools)
    
    @patch("x402_langchain.agent.hub")
    @patch("x402_langchain.agent.create_react_agent")
    def test_create_agent_with_llm(self, mock_create_react, mock_hub, mock_llm):
        """Test creating agent with just LLM"""
        # Mock hub.pull
        mock_prompt = Mock()
        mock_hub.pull.return_value = mock_prompt
        
        # Mock create_react_agent
        mock_agent = Mock()
        mock_create_react.return_value = mock_agent
        
        # Create agent
        agent = create_x402_agent(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            llm=mock_llm,
            spending_limit_daily=25.0,
            verbose=True,
        )
        
        assert isinstance(agent, X402Agent)
        mock_hub.pull.assert_called_once_with("hwchase17/react")
        mock_create_react.assert_called_once()
    
    def test_create_agent_requires_base_or_llm(self):
        """Test error when neither base_agent nor llm provided"""
        with pytest.raises(ValueError) as exc_info:
            create_x402_agent(
                private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            )
        
        assert "Either base_agent or llm must be provided" in str(exc_info.value)
    
    def test_create_agent_with_custom_config(self, mock_base_agent):
        """Test creating agent with custom configuration"""
        agent = create_x402_agent(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            base_agent=mock_base_agent,
            spending_limit_daily=75.0,
            spending_limit_per_request=2.5,
            auto_approve=False,
            allowed_domains=["api.trusted.com"],
            webhook_url="https://webhook.test.com",
        )
        
        assert agent.config.spending_limits.per_day == 75.0
        assert agent.config.spending_limits.per_request == 2.5
        assert agent.config.auto_approve is False
        assert agent.config.allowed_domains == ["api.trusted.com"]
        assert agent.config.webhook_url == "https://webhook.test.com"