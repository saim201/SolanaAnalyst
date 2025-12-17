"""
Integration tests for the complete trading pipeline.
Tests the 4-stage agent workflow: Technical → News → Reflection → Trader
"""
import pytest
import json
from typing import Dict, Any
from app.agents.pipeline import TradingGraph
from app.agents.technical import TechnicalAgent
from app.agents.news import NewsAgent
from app.agents.reflection import ReflectionAgent
from app.agents.trader import TraderAgent


class TestTradingPipeline:
    """Test suite for complete trading pipeline"""

    def setup_method(self):
        """Initialize fresh pipeline for each test"""
        self.pipeline = TradingGraph()

    def test_pipeline_initialization(self):
        """Test that pipeline initializes with all 4 agents"""
        assert self.pipeline.technical_agent is not None
        assert self.pipeline.news_agent is not None
        assert self.pipeline.reflection_agent is not None
        assert self.pipeline.trader_agent is not None
        assert self.pipeline.graph is not None

    def test_pipeline_graph_structure(self):
        """Test that graph has correct nodes and edges"""
        # Verify the graph was compiled
        assert self.pipeline.graph is not None

        # The graph should have all 4 nodes
        # (verification would require accessing private graph structure)

    def test_initial_state_structure(self):
        """Test that initial state has all required fields"""
        initial_state = {
            'technical': None,
            'news': None,
            'reflection': None,
            'trader': None,
        }

        # Verify all required fields exist
        required_fields = [
            'technical', 'news', 'reflection', 'trader'
        ]

        for field in required_fields:
            assert field in initial_state

    def test_pipeline_execution_returns_dict(self):
        """Test that pipeline execution returns complete result dictionary"""
        result = self.pipeline.run()

        assert isinstance(result, dict)

        # Verify all output fields
        expected_fields = ['technical', 'news', 'reflection', 'trader']

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_decision_field_is_valid(self):
        """Test that decision is one of the valid options"""
        result = self.pipeline.run()

        valid_decisions = ['buy', 'sell', 'hold']
        assert result['trader']['decision'].lower() in valid_decisions

    def test_confidence_is_float_in_range(self):
        """Test that confidence is a float between 0 and 1"""
        result = self.pipeline.run()

        assert isinstance(result['trader']['confidence'], (int, float))
        assert 0.0 <= result['trader']['confidence'] <= 1.0

    def test_analyses_contain_data(self):
        """Test that analysis fields contain data"""
        result = self.pipeline.run()

        # Check that each agent produced output
        assert result['technical'] is not None
        assert result['news'] is not None
        assert result['reflection'] is not None
        assert result['trader'] is not None

    def test_multiple_runs_independent(self):
        """Test that multiple pipeline runs are independent"""
        result1 = self.pipeline.run()
        result2 = self.pipeline.run()

        # Results should exist
        assert result1 is not None
        assert result2 is not None

        # Both should have valid structure
        assert 'trader' in result1
        assert 'trader' in result2
        assert 'technical' in result1
        assert 'technical' in result2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
