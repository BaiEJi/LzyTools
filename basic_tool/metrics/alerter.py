"""
Metrics 告警评估器。

根据 AlertRule 对当前指标值进行评估，管理告警状态机（OK → PENDING → FIRING → OK）。
纯同步逻辑，不依赖 async、数据库或网络。
"""

import math
import re
from datetime import datetime, timedelta

from loguru import logger

from basic_tool.metrics.models import AlertEvent, AlertRule, AlertState


class AlertEvaluator:
    """告警评估器，管理告警状态机和冷却逻辑。

    状态机流转: OK → PENDING → FIRING → OK。

    使用示例::

        evaluator = AlertEvaluator()
        rule = AlertRule(name="high_cpu", metric="cpu_usage", condition="> 80")
        event = evaluator.evaluate(rule, current_value=95.0)
        if event and event.state == AlertState.FIRING:
            send_notification(event)
    """

    def __init__(self) -> None:
        """初始化评估器，状态字典和最后告警时间字典均为空。"""
        self._states: dict[str, AlertState] = {}
        self._last_alert_time: dict[str, datetime] = {}

    def evaluate(
        self, rule: AlertRule, current_value: float, now: datetime | None = None
    ) -> AlertEvent | None:
        """评估告警规则，返回告警事件或 None。

        Args:
            rule: 告警规则。
            current_value: 当前指标值。
            now: 当前时间，默认 datetime.now()。

        Returns:
            AlertEvent 或 None（无状态变化或被冷却抑制时）。

        Raises:
            ValueError: 条件格式无效时抛出。
        """
        if now is None:
            now = datetime.now()

        if not rule.enabled:
            return None

        operator, threshold = self._parse_condition(rule.condition)

        if math.isnan(current_value):
            return None

        is_breaching = self._compare(current_value, operator, threshold)

        rule_name = rule.name
        current_state = self._states.get(rule_name, AlertState.OK)

        if is_breaching:
            if current_state == AlertState.OK:
                self._states[rule_name] = AlertState.PENDING
                self._last_alert_time[rule_name] = now
                return AlertEvent(
                    rule_name=rule_name,
                    state=AlertState.PENDING,
                    value=current_value,
                    threshold=threshold,
                    fired_at=now,
                )
            elif current_state == AlertState.PENDING:
                duration_td = self._parse_duration(rule.duration)
                first_breach_time = self._last_alert_time.get(rule_name)
                if first_breach_time and (now - first_breach_time) >= duration_td:
                    self._states[rule_name] = AlertState.FIRING
                    self._last_alert_time[rule_name] = now
                    logger.warning(
                        "alert firing | rule={} value={} threshold={}",
                        rule_name,
                        current_value,
                        threshold,
                    )
                    return AlertEvent(
                        rule_name=rule_name,
                        state=AlertState.FIRING,
                        value=current_value,
                        threshold=threshold,
                        fired_at=now,
                    )
                return None
            elif current_state == AlertState.FIRING:
                if self._in_cooldown(rule_name, rule, now):
                    return None
                self._last_alert_time[rule_name] = now
                return AlertEvent(
                    rule_name=rule_name,
                    state=AlertState.FIRING,
                    value=current_value,
                    threshold=threshold,
                    fired_at=now,
                )
        else:
            if current_state in (AlertState.PENDING, AlertState.FIRING):
                self._states.pop(rule_name, None)
                self._last_alert_time.pop(rule_name, None)
                logger.info("alert resolved | rule={} value={}", rule_name, current_value)
                return AlertEvent(
                    rule_name=rule_name,
                    state=AlertState.OK,
                    value=current_value,
                    threshold=threshold,
                    resolved_at=now,
                )
        return None

    def get_state(self, rule_name: str) -> AlertState:
        """获取指定规则的当前状态。

        Args:
            rule_name: 规则名称。

        Returns:
            当前状态，未跟踪时返回 AlertState.OK。
        """
        return self._states.get(rule_name, AlertState.OK)

    def get_all_states(self) -> dict[str, AlertState]:
        """获取所有规则的当前状态（防御性拷贝）。

        Returns:
            规则名到状态的字典副本。
        """
        return dict(self._states)

    def _compare(self, value: float, operator: str, threshold: float) -> bool:
        """比较值与阈值。"""
        if operator == ">":
            return value > threshold
        if operator == ">=":
            return value >= threshold
        if operator == "<":
            return value < threshold
        if operator == "<=":
            return value <= threshold
        if operator == "==":
            return value == threshold
        if operator == "!=":
            return value != threshold
        return False

    def _in_cooldown(self, rule_name: str, rule: AlertRule, now: datetime) -> bool:
        """检查规则是否处于冷却期内。"""
        last = self._last_alert_time.get(rule_name)
        if last is None:
            return False
        cooldown_td = self._parse_duration(rule.cooldown)
        return (now - last) < cooldown_td

    @staticmethod
    def _parse_condition(condition: str) -> tuple[str, float]:
        """解析条件字符串为 (运算符, 阈值)。

        Args:
            condition: 条件字符串，如 "> 80"。

        Returns:
            (运算符, 阈值) 元组。

        Raises:
            ValueError: 条件格式无效时抛出。
        """
        match = re.match(r"^\s*(>=|<=|!=|==|>|<)\s*([\d.]+)\s*$", condition)
        if not match:
            raise ValueError(f"Invalid condition format: {condition}")
        return match.group(1), float(match.group(2))

    @staticmethod
    def _parse_duration(duration: str) -> timedelta:
        """解析时长字符串为 timedelta。

        Args:
            duration: 时长字符串，如 "5m"、"30s"、"2h"、"1d"。

        Returns:
            对应的 timedelta 对象。

        Raises:
            ValueError: 时长格式无效时抛出。
        """
        match = re.match(r"^\s*(\d+)\s*([smhd])\s*$", duration)
        if not match:
            raise ValueError(f"Invalid duration format: {duration}")
        value = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return timedelta(seconds=value * multipliers[unit])
