"""
Unit tests for individual trading agents.
Tests each agent's functionality in isolation.
"""
import pytest
import json
from app.agents.base import BaseAgent, AgentState
from app.agents.technical import TechnicalAgent
from app.agents.news import NewsAgent
from app.agents.reflection import ReflectionAgent
from app.agents.risk_management import RiskManagementAgent
from app.agents.trader import TraderAgent
from app.agents.portfolio import PortfolioAgent


class TestBaseAgent:
    """Test suite for BaseAgent abstract class"""

    def test_base_agent_is_abstract(self):
        """Test that BaseAgent cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseAgent()

    def test_base_agent_requires_execute_implementation(self):
        """Test that subclasses must implement execute method"""

        class IncompleteAgent(BaseAgent):
            pass

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_agent_state_type(self):
        """Test AgentState TypedDict has required fields"""
        state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': 'test',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        assert state['decision'] in ['buy', 'sell', 'hold']
        assert 0.0 <= state['confidence'] <= 1.0
        assert -1.0 <= state['action'] <= 1.0


class TestTechnicalAgent:
    """Unit tests for TechnicalAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = TechnicalAgent()

    def test_agent_initialization(self):
        """Test that agent initializes with correct model"""
        assert self.agent.model == "claude-3-5-haiku-20241022"
        assert self.agent.temperature == 0.3

    def test_agent_is_callable(self):
        """Test that agent can be called as a function"""
        assert callable(self.agent)

    def test_agent_has_execute_method(self):
        """Test that agent has execute method"""
        assert hasattr(self.agent, 'execute')
        assert callable(self.agent.execute)

    def test_agent_state_passthrough(self):
        """Test that agent preserves input state fields"""
        initial_state: AgentState = {
            'indicators_analysis': '',
            'news_analysis': 'test_news',
            'reflection_analysis': 'test_reflection',
            'reasoning': 'test_reason',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        # Original fields should be preserved
        assert result['news_analysis'] == 'test_news'
        assert result['reflection_analysis'] == 'test_reflection'
        assert result['reasoning'] == 'test_reason'


class TestNewsAgent:
    """Unit tests for NewsAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = NewsAgent()

    def test_agent_initialization(self):
        """Test that agent initializes with correct model"""
        assert self.agent.model == "claude-3-5-haiku-20241022"
        assert self.agent.temperature == 0.3

    def test_agent_inherits_from_base(self):
        """Test that NewsAgent inherits from BaseAgent"""
        assert isinstance(self.agent, BaseAgent)

    def test_agent_produces_analysis(self):
        """Test that agent produces news analysis output"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert 'news_analysis' in result
        # Analysis should be a non-empty string
        assert isinstance(result['news_analysis'], str)


class TestReflectionAgent:
    """Unit tests for ReflectionAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = ReflectionAgent()

    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        assert hasattr(self.agent, 'model')
        assert hasattr(self.agent, 'temperature')

    def test_agent_inherits_from_base(self):
        """Test that ReflectionAgent inherits from BaseAgent"""
        assert isinstance(self.agent, BaseAgent)

    def test_agent_produces_reflection(self):
        """Test that agent produces reflection analysis"""
        initial_state: AgentState = {
            'indicators_analysis': 'test_indicators',
            'news_analysis': 'test_news',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert 'reflection_analysis' in result
        assert isinstance(result['reflection_analysis'], str)


class TestRiskManagementAgent:
    """Unit tests for RiskManagementAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = RiskManagementAgent()

    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        assert hasattr(self.agent, 'model')
        assert hasattr(self.agent, 'temperature')

    def test_agent_inherits_from_base(self):
        """Test that RiskManagementAgent inherits from BaseAgent"""
        assert isinstance(self.agent, BaseAgent)

    def test_agent_produces_risk_assessment(self):
        """Test that agent produces risk assessment"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'buy',
            'confidence': 0.7,
            'action': 0.8,
        }

        result = self.agent.execute(initial_state)

        assert 'risk_approved' in result
        assert 'position_size' in result
        assert 'max_loss' in result
        assert 'risk_reward' in result
        assert 'risk_reasoning' in result
        assert 'risk_warnings' in result

    def test_risk_values_are_valid(self):
        """Test that risk values are within valid ranges"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'buy',
            'confidence': 0.7,
            'action': 0.8,
        }

        result = self.agent.execute(initial_state)

        assert isinstance(result['risk_approved'], bool)
        assert isinstance(result['position_size'], (int, float))
        assert 0.0 <= result['position_size'] <= 1.0
        assert result['max_loss'] >= 0.0
        assert result['risk_reward'] >= 0.0

    def test_risk_warnings_is_list(self):
        """Test that risk_warnings is always a list"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert isinstance(result['risk_warnings'], list)


class TestTraderAgent:
    """Unit tests for TraderAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = TraderAgent()

    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        assert hasattr(self.agent, 'model')
        assert hasattr(self.agent, 'temperature')

    def test_agent_inherits_from_base(self):
        """Test that TraderAgent inherits from BaseAgent"""
        assert isinstance(self.agent, BaseAgent)

    def test_agent_produces_decision(self):
        """Test that agent produces trading decision"""
        initial_state: AgentState = {
            'indicators_analysis': 'Strong uptrend',
            'news_analysis': 'Positive sentiment',
            'reflection_analysis': 'Pattern confirmed',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert 'decision' in result
        assert 'confidence' in result
        assert 'action' in result
        assert 'reasoning' in result

    def test_decision_is_valid(self):
        """Test that decision is one of the valid options"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert result['decision'].lower() in ['buy', 'sell', 'hold']

    def test_confidence_in_valid_range(self):
        """Test that confidence is between 0 and 1"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert 0.0 <= result['confidence'] <= 1.0

    def test_action_in_valid_range(self):
        """Test that action is between -1 and 1"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert -1.0 <= result['action'] <= 1.0

    def test_reasoning_is_string(self):
        """Test that reasoning is a string"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        result = self.agent.execute(initial_state)

        assert isinstance(result['reasoning'], str)


class TestPortfolioAgent:
    """Unit tests for PortfolioAgent"""

    def setup_method(self):
        """Initialize agent for each test"""
        self.agent = PortfolioAgent()

    def test_agent_initialization(self):
        """Test that agent initializes correctly"""
        assert hasattr(self.agent, 'model')
        assert hasattr(self.agent, 'temperature')

    def test_agent_inherits_from_base(self):
        """Test that PortfolioAgent inherits from BaseAgent"""
        assert isinstance(self.agent, BaseAgent)

    def test_agent_produces_portfolio_analysis(self):
        """Test that agent produces portfolio analysis"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': 'Trade rationale',
            'decision': 'buy',
            'confidence': 0.7,
            'action': 0.8,
        }

        result = self.agent.execute(initial_state)

        assert 'portfolio_analysis' in result
        assert isinstance(result['portfolio_analysis'], str)

    def test_analysis_contains_meaningful_content(self):
        """Test that portfolio analysis contains meaningful output"""
        initial_state: AgentState = {
            'indicators_analysis': 'test',
            'news_analysis': 'test',
            'reflection_analysis': 'test',
            'reasoning': 'Trade rationale',
            'decision': 'buy',
            'confidence': 0.7,
            'action': 0.8,
        }

        result = self.agent.execute(initial_state)

        # Analysis should not be empty
        assert len(result['portfolio_analysis']) > 0


class TestAgentStateManagement:
    """Test state management across agents"""

    def test_state_immutability(self):
        """Test that agent doesn't corrupt original state"""
        original_state: AgentState = {
            'indicators_analysis': 'original_indicators',
            'news_analysis': 'original_news',
            'reflection_analysis': 'original_reflection',
            'reasoning': 'original_reasoning',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
        }

        agent = NewsAgent()
        result = agent.execute(original_state.copy())

        # Original state values should be preserved in result
        assert result['indicators_analysis'] == 'original_indicators'
        assert result['reasoning'] == 'original_reasoning'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
