"""Backpressure extreme scenario tests"""
import asyncio
import time
from typing import List

from crawlo.backpressure.strategies import QueueSizeStrategy, AdaptiveStrategy, CompositeStrategy
from crawlo.backpressure.interfaces import BackpressureStrategyConfig, PressureLevel
from crawlo.backpressure import BackpressureController


class ExtremeMockQueue:
    """Mock queue that simulates real-time size changes for extreme scenarios"""
    def __init__(self, max_size: int = 100):
        self._size: int = 0
        self.max_size = max_size
        self._enqueue_count: int = 0
        self._dequeue_count: int = 0
        self._sleep_time: float = 0.001  # Simulate processing time

    async def size(self) -> int:
        return self._size

    def enqueue(self, count: int = 1):
        self._size = min(self._size + count, self.max_size)
        self._enqueue_count += count

    def dequeue(self, count: int = 1):
        self._size = max(self._size - count, 0)
        self._dequeue_count += count


async def test_rush_scenario():
    """Rush: sudden burst fills queue to 100%, verify backpressure escalation"""
    print("\n=== Test 1: Rush Scenario ===")
    config = BackpressureStrategyConfig(threshold=0.5, base_delay=0.5, max_delay=5.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=config))
    queue = ExtremeMockQueue(max_size=100)

    delays: List[float] = []
    levels: List[PressureLevel] = []

    # Simulate burst: 10 items at a time until full
    for batch in range(15):
        queue.enqueue(10)

        active = await bc.should_apply(queue)
        delay = await bc.calculate_delay(queue)
        metrics = await bc.get_metrics(queue)

        delays.append(delay)
        levels.append(metrics.level)

        # Simulate slow processing: dequeue 3 per batch
        queue.dequeue(3)

    # Verify progression: delay should increase as queue fills up
    assert delays[-5] > delays[0], f"Delay should escalate: {delays}"
    assert PressureLevel.CRITICAL in levels, f"Should reach CRITICAL level: {levels}"
    utilization = queue._size / queue.max_size
    print(f"  Queue: {queue._size}/{queue.max_size} ({utilization:.0%})")
    print(f"  Delays: min={min(delays):.2f}s, max={max(delays):.2f}s")
    print(f"  Levels seen: {set(l.value for l in levels)}")
    print("  PASSED")


async def test_oscillation_scenario():
    """Oscillation: queue rapidly fills and drains, verify controller responds"""
    print("\n=== Test 2: Oscillation Scenario ===")
    config = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=3.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=config))
    queue = ExtremeMockQueue(max_size=100)

    state_changes = 0
    prev_active = False

    # 5 cycles of fill → drain
    for cycle in range(5):
        # Fill phase: enqueue rapidly
        for _ in range(8):
            queue.enqueue(15)
            active = await bc.should_apply(queue)
            if active != prev_active:
                state_changes += 1
                prev_active = active

        # Drain phase: dequeue rapidly
        for _ in range(5):
            queue.dequeue(20)
            active = await bc.should_apply(queue)
            if active != prev_active:
                state_changes += 1
                prev_active = active

    # Should have at least 4 state changes (fill→drain→fill→drain...)
    assert state_changes >= 4, f"Expected >=4 state changes, got {state_changes}"
    # Should end near empty
    assert queue._size < 30, f"Queue should drain, got {queue._size}"
    print(f"  Final queue size: {queue._size}")
    print(f"  State changes: {state_changes}")
    print(f"  Stats: {bc.get_stats()}")
    print("  PASSED")


async def test_composite_extreme():
    """CompositeStrategy: combine QueueSize + Adaptive under extreme load"""
    print("\n=== Test 3: CompositeStrategy Under Extreme Load ===")
    config = BackpressureStrategyConfig(threshold=0.6, base_delay=0.5, max_delay=5.0)
    qs = QueueSizeStrategy(config=config)
    adapt = AdaptiveStrategy(config=config)
    cs = CompositeStrategy([qs, adapt])
    bc = BackpressureController(strategy=cs)
    queue = ExtremeMockQueue(max_size=100)

    delays_qs: List[float] = []
    delays_cs: List[float] = []

    # Fill to critical levels step by step
    for size_pct in [30, 50, 70, 85, 95, 99]:
        queue._size = size_pct
        delay = await bc.calculate_delay(queue)
        delays_cs.append(delay)

        # Compare: Composite should be >= individual strategies
        qs_delay = await qs.calculate_delay(queue)
        delays_qs.append(qs_delay)
        assert delay >= qs_delay, f"Composite delay {delay} < QS delay {qs_delay}"

    # At 99%, should be at max
    assert delays_cs[-1] >= config.max_delay * 0.8, f"Near-full should have high delay, got {delays_cs[-1]}"
    print(f"  QS delays:     {[f'{d:.1f}' for d in delays_qs]}")
    print(f"  Composite delays: {[f'{d:.1f}' for d in delays_cs]}")
    print("  PASSED")


async def test_adaptive_learning():
    """AdaptiveStrategy: sustained pressure should lower dynamic threshold"""
    print("\n=== Test 4: AdaptiveStrategy Dynamic Threshold Learning ===")
    config = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=5.0)
    adapt = AdaptiveStrategy(config=config)
    queue = ExtremeMockQueue(max_size=100)

    initial_threshold = adapt._dynamic_threshold

    # Feed in many high delays → threshold should decrease (more aggressive)
    for _ in range(20):
        adapt.record_delay(2.0)  # High delay feedback

    # Let adaptation update (need time to pass for throttle)
    adapt._last_update_time = time.time() - 2.0  # Simulate time passing
    queue._size = 55  # 55% — near initial threshold
    await adapt._update_dynamic_threshold()

    # Dynamic threshold should have moved
    assert adapt._dynamic_threshold != initial_threshold, \
        f"Threshold should have changed from {initial_threshold}"

    print(f"  Initial threshold: {initial_threshold:.2f}")
    print(f"  Final threshold:   {adapt._dynamic_threshold:.2f}")
    print(f"  Delay history size: {len(adapt._delay_history)}")
    print("  PASSED")


async def test_concurrent_enqueue_race():
    """Concurrent: multiple coroutines enqueuing while backpressure active"""
    print("\n=== Test 5: Concurrent Enqueue Under Backpressure ===")
    config = BackpressureStrategyConfig(threshold=0.3, base_delay=0.1, max_delay=2.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=config))
    queue = ExtremeMockQueue(max_size=50)

    # Pre-fill to 80% (above 30% threshold)
    queue._size = 40

    results: List[bool] = []

    async def enqueue_worker(worker_id: int):
        for _ in range(10):
            if await bc.should_apply(queue):
                delay = await bc.calculate_delay(queue)
                if delay > 0:
                    queue.enqueue(1)
            results.append(True)

    # 5 concurrent workers
    await asyncio.gather(*[enqueue_worker(i) for i in range(5)])

    # Queue should be at or near max (backpressure slows but doesn't stop)
    utilization = queue._size / queue.max_size
    assert utilization >= 0.7, f"Queue should stay high under pressure: {utilization:.0%}"
    assert len(results) == 50, f"All 50 operations should complete, got {len(results)}"

    print(f"  Queue utilization: {utilization:.0%}")
    print(f"  All workers completed: {len(results)} ops")
    print(f"  Backpressure activations: {bc.get_stats()['apply_count']}")
    print("  PASSED")


async def test_recovery_scenario():
    """Recovery: from 100% full to drain, verify backpressure releases"""
    print("\n=== Test 6: Recovery Scenario ===")
    config = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=3.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=config))
    queue = ExtremeMockQueue(max_size=100)

    # Start at 100% full
    queue._size = 100
    initial_active = await bc.should_apply(queue)
    assert initial_active is True

    # Gradually drain
    drain_steps = []
    while queue._size > 0:
        active = await bc.should_apply(queue)
        delay = await bc.calculate_delay(queue)
        drain_steps.append((queue._size, delay, active))
        queue.dequeue(10)

    # Last step should NOT be active (drained)
    final_size, final_delay, final_active = drain_steps[-1]
    assert final_active is False, f"Should release backpressure when drained, got active={final_active}"
    assert final_delay == 0.0, f"Drained queue should have 0 delay, got {final_delay}"

    print(f"  Drain steps: {len(drain_steps)}")
    print(f"  First: size={drain_steps[0][0]}, delay={drain_steps[0][1]:.1f}s, active={drain_steps[0][2]}")
    print(f"  Last:  size={final_size}, delay={final_delay}s, active={final_active}")
    print("  PASSED")


async def run_all():
    start = time.time()
    tests = [
        test_rush_scenario,
        test_oscillation_scenario,
        test_composite_extreme,
        test_adaptive_learning,
        test_concurrent_enqueue_race,
        test_recovery_scenario,
    ]
    passed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()

    duration = time.time() - start
    print(f"\n{'='*50}")
    print(f"EXTREME SCENARIOS: {passed}/{len(tests)} PASSED ({duration:.2f}s)")
    return passed


if __name__ == "__main__":
    asyncio.run(run_all())
