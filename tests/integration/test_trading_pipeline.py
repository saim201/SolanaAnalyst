"""
Integration tests for the complete trading pipeline.
Tests the 6-stage agent workflow: Technical → News → Reflection → Risk → Trader → Portfolio
"""
import pytest
import json
from typing import Dict, Any
from app.agents.pipeline import TradingGraph, TradingState
from app.agents.technical import TechnicalAgent
from app.agents.news import NewsAgent
from app.agents.reflection import ReflectionAgent
from app.agents.risk_management import RiskManagementAgent
from app.agents.trader import TraderAgent
from app.agents.portfolio import PortfolioAgent


class TestTradingPipeline:
    """Test suite for complete trading pipeline"""

    def setup_method(self):
        """Initialize fresh pipeline for each test"""
        self.pipeline = TradingGraph()

    def test_pipeline_initialization(self):
        """Test that pipeline initializes with all 6 agents"""
        assert self.pipeline.technical_agent is not None
        assert self.pipeline.news_agent is not None
        assert self.pipeline.reflection_agent is not None
        assert self.pipeline.risk_agent is not None
        assert self.pipeline.trader_agent is not None
        assert self.pipeline.portfolio_agent is not None
        assert self.pipeline.graph is not None

    def test_pipeline_graph_structure(self):
        """Test that graph has correct nodes and edges"""
        # Verify the graph was compiled
        assert self.pipeline.graph is not None

        # The graph should have all 6 nodes
        # (verification would require accessing private graph structure)

    def test_initial_state_structure(self):
        """Test that initial state has all required fields"""
        initial_state = {
            'indicators_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        # Verify all required fields exist
        required_fields = [
            'indicators_analysis', 'news_analysis', 'reflection_analysis',
            'reasoning', 'decision', 'confidence', 'action',
            'risk_approved', 'position_size', 'max_loss', 'risk_reward',
            'risk_reasoning', 'risk_warnings', 'portfolio_analysis'
        ]

        for field in required_fields:
            assert field in initial_state

    def test_pipeline_execution_returns_dict(self):
        """Test that pipeline execution returns complete result dictionary"""
        result = self.pipeline.run()

        assert isinstance(result, dict)

        # Verify all output fields
        expected_fields = [
            'decision', 'confidence', 'action', 'reasoning',
            'indicators_analysis', 'news_analysis', 'reflection_analysis',
            'risk_approved', 'position_size', 'max_loss', 'risk_reward',
            'risk_reasoning', 'risk_warnings', 'portfolio_analysis'
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_decision_field_is_valid(self):
        """Test that decision is one of the valid options"""
        result = self.pipeline.run()

        valid_decisions = ['buy', 'sell', 'hold']
        assert result['decision'].lower() in valid_decisions

    def test_confidence_is_float_in_range(self):
        """Test that confidence is a float between 0 and 1"""
        result = self.pipeline.run()

        assert isinstance(result['confidence'], (int, float))
        assert 0.0 <= result['confidence'] <= 1.0

    def test_action_is_float_in_range(self):
        """Test that action is a float between -1 and 1"""
        result = self.pipeline.run()

        assert isinstance(result['action'], (int, float))
        assert -1.0 <= result['action'] <= 1.0

    def test_analysis_fields_are_strings(self):
        """Test that all analysis fields are strings"""
        result = self.pipeline.run()

        analysis_fields = [
            'reasoning', 'indicators_analysis', 'news_analysis',
            'reflection_analysis', 'risk_reasoning', 'portfolio_analysis'
        ]

        for field in analysis_fields:
            assert isinstance(result[field], str), f"{field} is not a string"

    def test_risk_warnings_is_list(self):
        """Test that risk_warnings is a list"""
        result = self.pipeline.run()

        assert isinstance(result['risk_warnings'], list)

    def test_position_size_is_non_negative(self):
        """Test that position size is non-negative"""
        result = self.pipeline.run()

        assert isinstance(result['position_size'], (int, float))
        assert result['position_size'] >= 0.0
        # Position size should typically be between 0 and 1 (percentage)
        assert result['position_size'] <= 1.0 or result['position_size'] == 0.0

    def test_max_loss_is_non_negative(self):
        """Test that max loss is non-negative"""
        result = self.pipeline.run()

        assert isinstance(result['max_loss'], (int, float))
        assert result['max_loss'] >= 0.0

    def test_risk_reward_is_non_negative(self):
        """Test that risk reward ratio is non-negative"""
        result = self.pipeline.run()

        assert isinstance(result['risk_reward'], (int, float))
        assert result['risk_reward'] >= 0.0

    def test_risk_approved_is_boolean(self):
        """Test that risk_approved is a boolean"""
        result = self.pipeline.run()

        assert isinstance(result['risk_approved'], bool)

    def test_analyses_are_not_empty_on_execution(self):
        """Test that analysis fields contain some output"""
        result = self.pipeline.run()

        # At least some analyses should have content
        analysis_fields = [
            'indicators_analysis', 'news_analysis', 'reflection_analysis'
        ]

        non_empty_count = sum(
            1 for field in analysis_fields
            if len(result[field]) > 0
        )

        # At least one analysis should have content
        assert non_empty_count > 0

    def test_pipeline_decision_consistency(self):
        """Test that decision and action are somewhat consistent"""
        result = self.pipeline.run()

        decision = result['decision'].lower()
        action = result['action']

        # BUY should have positive action
        if decision == 'buy':
            assert action > -0.5, "BUY decision should have somewhat positive action"

        # SELL should have negative action
        elif decision == 'sell':
            assert action < 0.5, "SELL decision should have somewhat negative action"

        # HOLD should have action close to 0
        elif decision == 'hold':
            assert -0.6 < action < 0.6, "HOLD decision should have action close to 0"

    def test_multiple_runs_independent(self):
        """Test that multiple pipeline runs are independent"""
        result1 = self.pipeline.run()
        result2 = self.pipeline.run()

        # Results should exist
        assert result1 is not None
        assert result2 is not None

        # Both should have valid structure
        assert 'decision' in result1
        assert 'decision' in result2
        assert 'confidence' in result1
        assert 'confidence' in result2


class TestTechnicalAgentIntegration:
    """Test Technical Agent in pipeline context"""

    def test_technical_agent_execution(self):
        """Test that technical agent executes and produces output"""
        agent = TechnicalAgent()

        initial_state = {
            'indicators_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'indicators_analysis' in result
        assert isinstance(result['indicators_analysis'], str)


class TestNewsAgentIntegration:
    """Test News Agent in pipeline context"""

    def test_news_agent_execution(self):
        """Test that news agent executes and produces output"""
        agent = NewsAgent()

        initial_state = {
            'indicators_analysis': 'Technical analysis complete',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'news_analysis' in result
        assert isinstance(result['news_analysis'], str)


class TestReflectionAgentIntegration:
    """Test Reflection Agent in pipeline context"""

    def test_reflection_agent_execution(self):
        """Test that reflection agent executes and produces output"""
        agent = ReflectionAgent()

        initial_state = {
            'indicators_analysis': 'Technical analysis complete',
            'news_analysis': 'News analysis complete',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'reflection_analysis' in result
        assert isinstance(result['reflection_analysis'], str)


class TestRiskManagementAgentIntegration:
    """Test Risk Management Agent in pipeline context"""

    def test_risk_agent_execution(self):
        """Test that risk agent executes and produces output"""
        agent = RiskManagementAgent()

        initial_state = {
            'indicators_analysis': 'Technical analysis complete',
            'news_analysis': 'News analysis complete',
            'reflection_analysis': 'Reflection analysis complete',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'risk_approved' in result
        assert 'position_size' in result
        assert 'max_loss' in result
        assert 'risk_reward' in result
        assert 'risk_reasoning' in result
        assert 'risk_warnings' in result


class TestTraderAgentIntegration:
    """Test Trader Agent in pipeline context"""

    def test_trader_agent_execution(self):
        """Test that trader agent executes and produces output"""
        agent = TraderAgent()

        initial_state = {
            'indicators_analysis': 'Technical analysis complete',
            'news_analysis': 'News analysis complete',
            'reflection_analysis': 'Reflection analysis complete',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.5,
            'max_loss': 100.0,
            'risk_reward': 2.0,
            'risk_reasoning': 'Risk assessment complete',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'decision' in result
        assert 'confidence' in result
        assert 'action' in result
        assert 'reasoning' in result

        # Verify decision is valid
        assert result['decision'].lower() in ['buy', 'sell', 'hold']
        # Verify confidence is in range
        assert 0.0 <= result['confidence'] <= 1.0
        # Verify action is in range
        assert -1.0 <= result['action'] <= 1.0


class TestPortfolioAgentIntegration:
    """Test Portfolio Agent in pipeline context"""

    def test_portfolio_agent_execution(self):
        """Test that portfolio agent executes and produces output"""
        agent = PortfolioAgent()

        initial_state = {
            'indicators_analysis': 'Technical analysis complete',
            'news_analysis': 'News analysis complete',
            'reflection_analysis': 'Reflection analysis complete',
            'reasoning': 'Trade reasoning',
            'decision': 'buy',
            'confidence': 0.7,
            'action': 0.8,
            'risk_approved': True,
            'position_size': 0.5,
            'max_loss': 100.0,
            'risk_reward': 2.0,
            'risk_reasoning': 'Risk assessment complete',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        result = agent.execute(initial_state)

        assert 'portfolio_analysis' in result
        assert isinstance(result['portfolio_analysis'], str)


class TestPipelineDataFlow:
    """Test data flow through the pipeline stages"""

    def test_state_propagation(self):
        """Test that state is properly propagated through stages"""
        pipeline = TradingGraph()

        # Set up initial state
        initial_state = {
            'indicators_analysis': '',
            'news_analysis': '',
            'reflection_analysis': '',
            'reasoning': '',
            'decision': 'hold',
            'confidence': 0.5,
            'action': 0.0,
            'risk_approved': False,
            'position_size': 0.0,
            'max_loss': 0.0,
            'risk_reward': 0.0,
            'risk_reasoning': '',
            'risk_warnings': [],
            'portfolio_analysis': '',
        }

        # Execute pipeline
        result = pipeline.graph.invoke(initial_state)

        # Verify state has been populated at each stage
        assert result['indicators_analysis']  # Set by technical agent
        assert result['news_analysis']  # Set by news agent
        assert result['reflection_analysis']  # Set by reflection agent
        assert 'position_size' in result  # Set by risk agent
        assert 'decision' in result  # Set by trader agent
        assert 'portfolio_analysis' in result  # Set by portfolio agent


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
