"""IDGenerator 测试。"""

from unittest.mock import patch

import pytest

from basic_tool.id_generator.config import IDConfig
from basic_tool.id_generator.generator import IDGenerator


class TestIDGenerator:
    """IDGenerator 核心功能测试。"""

    def test_new_returns_positive_int(self):
        """返回正整数。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.new()
        assert isinstance(result, int)
        assert result > 0

    def test_new_64bit(self):
        """值 < 2^63。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.new()
        assert result < (1 << 63)

    def test_new_unique(self):
        """生成 10000 个 ID 无重复。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        ids = [gen.new() for _ in range(10000)]
        assert len(set(ids)) == 10000

    def test_new_monotonic(self):
        """连续生成严格递增。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        prev = gen.new()
        for _ in range(1000):
            curr = gen.new()
            assert curr > prev
            prev = curr

    def test_batch_count(self):
        """batch(100) 返回 100 个元素。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.batch(100)
        assert len(result) == 100

    def test_batch_unique(self):
        """批量内无重复。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.batch(100)
        assert len(set(result)) == 100

    def test_batch_monotonic(self):
        """批量内严格递增。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.batch(100)
        for i in range(99):
            assert result[i] < result[i + 1]

    def test_batch_zero_raises(self):
        """batch(0) 抛 ValueError。"""
        gen = IDGenerator(IDConfig())
        with pytest.raises(ValueError, match="count must be > 0"):
            gen.batch(0)

    def test_batch_negative_raises(self):
        """batch(-1) 抛 ValueError。"""
        gen = IDGenerator(IDConfig())
        with pytest.raises(ValueError, match="count must be > 0"):
            gen.batch(-1)

    def test_new_prefixed(self):
        """格式正确 "ORD_123456"。"""
        gen = IDGenerator(IDConfig(worker_id=1))
        result = gen.new_prefixed("ORD")
        assert result.startswith("ORD_")
        assert result[4:].isdigit()

    def test_different_worker_ids(self):
        """不同 worker_id 生成的 ID 不冲突（同秒内）。"""
        gen_a = IDGenerator(IDConfig(worker_id=0))
        gen_b = IDGenerator(IDConfig(worker_id=1))
        ids_a = set(gen_a.batch(100))
        ids_b = set(gen_b.batch(100))
        assert not ids_a.intersection(ids_b)

    def test_clock_backward(self):
        """时钟回拨场景 — 验证生成不挂起。

        Mock _current_ms to first return T, then T-100 (backward),
        then T+1 (recovery). ID generation should still work.
        """
        gen = IDGenerator(IDConfig(worker_id=1))
        # Get a real first ID to establish _last_ts
        gen.new()

        current_time = gen._last_ts
        mock_times = iter([current_time - 100, current_time + 1])

        with patch.object(gen, "_current_ms", side_effect=lambda: next(mock_times)):
            # This should succeed — _wait_next_ms will see current_time + 1 > _last_ts
            result = gen.new()
            assert isinstance(result, int)
            assert result > 0

    def test_sequence_overflow(self):
        """同毫秒超过 4096 个 — 直接调用 _next_id_unlocked 触发溢出路径。

        Mock _current_ms to return a fixed timestamp, then call
        _next_id_unlocked 4097 times. The 4097th should trigger overflow
        and wait for next ms.
        """
        gen = IDGenerator(IDConfig(worker_id=1))
        fixed_ts = gen._current_ms()

        # After 4096 IDs in same ms, sequence overflows to 0,
        # triggering _wait_next_ms. We need to provide a future timestamp.
        call_count = 0

        def mock_time():
            nonlocal call_count
            call_count += 1
            if call_count <= 4097:
                return fixed_ts  # Same ms for first 4097 calls
            return fixed_ts + 1  # Next ms after overflow triggers wait

        with patch.object(gen, "_current_ms", side_effect=mock_time):
            with gen._lock:
                for _ in range(4096):
                    gen._next_id_unlocked()
                # 4097th call: sequence wraps to 0, triggers _wait_next_ms
                # which calls _current_ms again (4098th call -> fixed_ts + 1)
                result = gen._next_id_unlocked()
                assert result > 0
