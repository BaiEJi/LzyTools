"""
AlertEvaluator 告警评估器测试。

覆盖状态机流转、冷却、条件解析、NaN 处理等。
"""

from datetime import datetime, timedelta

import pytest

from basic_tool.metrics.alerter import AlertEvaluator
from basic_tool.metrics.models import AlertRule, AlertState


class TestAlertEvaluator:
    """AlertEvaluator 状态机和解析逻辑测试。"""

    def test_first_trigger_pending(self):
        """首次超阈值应返回 PENDING 事件。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80")
        event = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        assert event is not None
        assert event.state == AlertState.PENDING
        assert event.value == 95.0
        assert event.threshold == 80.0

    def test_pending_to_firing(self):
        """持续超阈值达到 duration 后应转为 FIRING。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80", duration="5m")
        first = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        assert first.state == AlertState.PENDING
        second = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 5))
        assert second.state == AlertState.FIRING

    def test_firing_to_ok(self):
        """值恢复正常应返回 OK 事件。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80", duration="5m")
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 5))
        event = evaluator.evaluate(rule, 50.0, now=datetime(2024, 1, 1, 12, 10))
        assert event is not None
        assert event.state == AlertState.OK
        assert event.resolved_at is not None

    def test_cooldown_suppresses(self):
        """冷却期内重复评估应返回 None。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="high_cpu", metric="cpu", condition="> 80", duration="5m", cooldown="10m")
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 5))
        event = evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 6))
        assert event is None

    def test_invalid_condition(self):
        """无效条件格式应抛出 ValueError。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="bad", metric="x", condition="invalid")
        with pytest.raises(ValueError, match="Invalid condition"):
            evaluator.evaluate(rule, 50.0)

    def test_nan_value(self):
        """NaN 值不应触发告警。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="nan_test", metric="x", condition="> 80")
        event = evaluator.evaluate(rule, float("nan"), now=datetime(2024, 1, 1))
        assert event is None

    def test_get_state(self):
        """get_state 返回当前状态，未跟踪时返回 OK。"""
        evaluator = AlertEvaluator()
        assert evaluator.get_state("nonexistent") == AlertState.OK
        rule = AlertRule(name="tracked", metric="x", condition="> 80")
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        assert evaluator.get_state("tracked") == AlertState.PENDING

    def test_get_all_states(self):
        """get_all_states 返回状态字典的防御性拷贝。"""
        evaluator = AlertEvaluator()
        rule = AlertRule(name="tracked", metric="x", condition="> 80")
        evaluator.evaluate(rule, 95.0, now=datetime(2024, 1, 1, 12, 0))
        states = evaluator.get_all_states()
        assert isinstance(states, dict)
        assert "tracked" in states
        states["new_key"] = AlertState.FIRING
        assert "new_key" not in evaluator.get_all_states()

    def test_parse_condition_operators(self):
        """解析所有 6 种运算符。"""
        assert AlertEvaluator._parse_condition("> 80") == (">", 80.0)
        assert AlertEvaluator._parse_condition(">= 80") == (">=", 80.0)
        assert AlertEvaluator._parse_condition("< 80") == ("<", 80.0)
        assert AlertEvaluator._parse_condition("<= 80") == ("<=", 80.0)
        assert AlertEvaluator._parse_condition("== 80") == ("==", 80.0)
        assert AlertEvaluator._parse_condition("!= 80") == ("!=", 80.0)

    def test_parse_duration_units(self):
        """解析所有 4 种时长单位。"""
        assert AlertEvaluator._parse_duration("30s") == timedelta(seconds=30)
        assert AlertEvaluator._parse_duration("5m") == timedelta(minutes=5)
        assert AlertEvaluator._parse_duration("2h") == timedelta(hours=2)
        assert AlertEvaluator._parse_duration("1d") == timedelta(days=1)
