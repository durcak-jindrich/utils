import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure the source directory is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import pr_reviewer_eval.main as eval_main

@pytest.fixture(autouse=True)
def reset_degrade_agent():
    eval_main.DEGRADE_AGENT = False
    yield
    eval_main.DEGRADE_AGENT = False

# --- 1. Unit Tests for JSON Parsing ---

def test_parse_json_response_clean():
    """Verify that clean JSON is correctly parsed."""
    data = '{"score": 0.8, "missed_issues": ["SQL Injection"]}'
    parsed = eval_main.parse_json_response(data)
    assert parsed["score"] == 0.8
    assert parsed["missed_issues"] == ["SQL Injection"]

def test_parse_json_response_markdown():
    """Verify that JSON wrapped in markdown code blocks is correctly parsed."""
    data = '```json\n{"score": 0.5, "missed_issues": []}\n```'
    parsed = eval_main.parse_json_response(data)
    assert parsed["score"] == 0.5
    assert parsed["missed_issues"] == []

def test_parse_json_response_messy():
    """Verify that JSON with leading/trailing text is correctly parsed."""
    data = 'Some preamble stuff here {\n  "score": 1.0\n} postamble'
    parsed = eval_main.parse_json_response(data)
    assert parsed["score"] == 1.0


# --- 2. Unit Tests for Agent and Mock Judges ---

def test_pr_reviewer_agent_normal():
    """Test that the agent returns expected issues in normal mode (mock)."""
    with patch.dict(os.environ, {"REAL_LLM": "false"}):
        eval_main.DEGRADE_AGENT = False
        diff = "def process_user_data(user_dict):\n    profile = user_dict.get('profile')"
        comments = eval_main.pr_reviewer_agent(diff)
        assert len(comments) == 1
        assert comments[0]["severity"] == "warning"
        assert "AttributeError" in comments[0]["comment"]

def test_pr_reviewer_agent_degraded():
    """Test that the agent misses issues when degraded (mock)."""
    with patch.dict(os.environ, {"REAL_LLM": "false"}):
        eval_main.DEGRADE_AGENT = True
        diff = "def process_user_data(user_dict):\n    profile = user_dict.get('profile')"
        comments = eval_main.pr_reviewer_agent(diff)
        assert len(comments) == 0

def test_issue_coverage_judge_normal():
    """Verify issue coverage judge calculates perfect score under normal execution."""
    agent_comments = [{"line": 5, "severity": "warning", "comment": "Null check missing"}]
    seeded_issues = ["Missing None check on profile"]
    score, missed = eval_main.run_issue_coverage_judge(agent_comments, seeded_issues)
    assert score == 1.0
    assert len(missed) == 0

def test_issue_coverage_judge_degraded():
    """Verify issue coverage judge detects missed issues when degraded."""
    eval_main.DEGRADE_AGENT = True
    agent_comments = []
    seeded_issues = ["Missing None check on profile"]
    score, missed = eval_main.run_issue_coverage_judge(agent_comments, seeded_issues)
    assert score == 0.0
    assert len(missed) == 1
    eval_main.DEGRADE_AGENT = False

def test_noise_ratio_judge_normal():
    """Verify noise ratio judge rates normal comments as non-noisy."""
    agent_comments = [{"line": 5, "severity": "warning", "comment": "Null check missing"}]
    diff = "def process_user_data(user_dict):\n"
    score, noisy = eval_main.run_noise_ratio_judge(agent_comments, diff)
    assert score == 1.0
    assert len(noisy) == 0

def test_noise_ratio_judge_degraded():
    """Verify noise ratio judge detects noise in degraded mode on clean code."""
    eval_main.DEGRADE_AGENT = True
    agent_comments = [{"line": 16, "severity": "suggestion", "comment": "Noisy suggestion"}]
    diff = "def calculate_average(numbers):\n"
    score, noisy = eval_main.run_noise_ratio_judge(agent_comments, diff)
    assert score == 0.0
    assert len(noisy) == 1
    eval_main.DEGRADE_AGENT = False

def test_comment_quality_judge_normal():
    """Verify quality score of normal comments."""
    comment = {"line": 5, "severity": "warning", "comment": "Missing error handling"}
    score, reason = eval_main.run_comment_quality_judge(comment)
    assert score == 1.0
    assert "actionable" in reason.lower() or "clear" in reason.lower()

def test_comment_quality_judge_degraded():
    """Verify lower quality score for degraded/noisy comment."""
    eval_main.DEGRADE_AGENT = True
    comment = {"line": 16, "severity": "suggestion", "comment": "Noisy suggestion"}
    score, reason = eval_main.run_comment_quality_judge(comment)
    assert score == 0.4
    assert "nitpick" in reason.lower()
    eval_main.DEGRADE_AGENT = False


# --- 3. Integration / End-to-End Simulation Test ---

def test_local_evaluation_pipeline_success():
    """Verify the entire offline evaluation loop runs without errors."""
    scores = eval_main.run_local_evaluation(eval_main.GOLDEN_EXAMPLES)
    assert "issue_coverage" in scores
    assert "noise_ratio" in scores
    assert "comment_quality" in scores
    # Ensure they are valid float percentages
    for val in scores.values():
        assert 0.0 <= val <= 1.0

def test_regression_test_runner_runs_without_exceptions():
    """Verify regression test runner function executes fully without throwing errors."""
    # Temporarily mock run_evaluation_pipeline to return predictable values to verify runner comparison logic
    baseline_mock = {"issue_coverage": 1.0, "noise_ratio": 1.0, "comment_quality": 1.0}
    degraded_mock = {"issue_coverage": 0.8, "noise_ratio": 0.8, "comment_quality": 0.9}
    
    def side_effect():
        if eval_main.DEGRADE_AGENT:
            return degraded_mock
        return baseline_mock

    with patch("pr_reviewer_eval.main.run_evaluation_pipeline", side_effect=side_effect):
        # This will test the print output and logic
        eval_main.run_regression_test()
