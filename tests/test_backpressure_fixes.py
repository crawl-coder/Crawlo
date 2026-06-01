"""Backpressure fixes verification tests"""
import asyncio

from crawlo.backpressure.strategies import QueueSizeStrategy, AdaptiveStrategy, CompositeStrategy
from crawlo.backpressure.interfaces import BackpressureStrategyConfig, BackpressureMetrics, PressureLevel
from crawlo.backpressure.metrics_collector import QueueMetrics
from crawlo.backpressure import BackpressureController


class _MockQueue:
    """Simple mock queue that supports the IQueue interface"""
    def __init__(self, size: int = 0, max_size: int = 100):
        self._size = size
        self.max_size = max_size

    async def size(self) -> int:
        return self._size


async def _run_all_tests():
    """Run all backpressure verification tests"""
    passed = 0
    failed = 0

    # 1. QueueMetrics / BackpressureMetrics no name collision
    qm = QueueMetrics(queue_size=5, queue_max_size=100)
    bm = BackpressureMetrics(queue_size=5, max_queue_size=100, utilization=0.05)
    assert type(qm).__name__ == "QueueMetrics"
    assert type(bm).__name__ == "BackpressureMetrics"
    print("1. PASS - No name collision between QueueMetrics / BackpressureMetrics")
    passed += 1

    # 2. AdaptiveStrategy.record_delay stores history
    config = BackpressureStrategyConfig(threshold=0.5, base_delay=0.1, max_delay=5.0)
    adapt = AdaptiveStrategy(config=config)
    adapt.record_delay(0.5)
    adapt.record_delay(0.8)
    assert len(adapt._delay_history) == 2
    print("2. PASS - AdaptiveStrategy.record_delay OK, history=2")
    passed += 1

    # 3. Engine EngineBackpressureAdapter delegates to unified module
    from crawlo.core.engine_helpers import EngineBackpressureAdapter as EngineBC
    ebc = EngineBC(max_queue_size=200, backpressure_ratio=0.9)
    assert hasattr(ebc, "_unified")
    stats = ebc.get_stats()
    assert stats["backpressure_ratio"] == 0.9
    print("3. PASS - Engine EngineBackpressureAdapter integration OK")
    passed += 1

    # 4. CompositeStrategy bug fix (no m.metrics access)
    config = BackpressureStrategyConfig(threshold=0.5)
    qs = QueueSizeStrategy(config=config)
    cs = CompositeStrategy([qs])
    queue = _MockQueue(size=50, max_size=100)
    metrics = await cs.get_metrics(queue)
    assert metrics.queue_size == 50
    assert metrics.utilization == 0.5
    print("4. PASS - CompositeStrategy.get_metrics() bug fixed")
    passed += 1

    # 5. High utilization (95%) triggers backpressure
    config2 = BackpressureStrategyConfig(threshold=0.5, base_delay=0.5, max_delay=5.0)
    strat = QueueSizeStrategy(config=config2)
    bc = BackpressureController(strategy=strat)
    queue2 = _MockQueue(size=95, max_size=100)
    active = await bc.should_apply(queue2)
    delay = await bc.calculate_delay(queue2)
    metrics2 = await bc.get_metrics(queue2)
    assert active is True
    assert delay > 0
    assert metrics2.level == PressureLevel.CRITICAL
    print(f"5. PASS - High utilization triggers backpressure (delay={delay:.2f}s, level={metrics2.level.value})")
    passed += 1

    # 6. Low utilization (40%) NO backpressure
    config3 = BackpressureStrategyConfig(threshold=0.5)
    bc2 = BackpressureController(strategy=QueueSizeStrategy(config=config3))
    queue3 = _MockQueue(size=40, max_size=100)
    active2 = await bc2.should_apply(queue3)
    delay2 = await bc2.calculate_delay(queue3)
    assert active2 is False
    assert delay2 == 0.0
    print(f"6. PASS - Low utilization no backpressure (active={active2})")
    passed += 1

    print(f"\n{'='*40}")
    print(f"ALL {passed} TESTS PASSED, 0 FAILED")
    return passed


def test_backpressure_fixes():
    """Entry point for pytest"""
    asyncio.run(_run_all_tests())


if __name__ == "__main__":
    asyncio.run(_run_all_tests())
