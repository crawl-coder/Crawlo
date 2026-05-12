"""Backpressure: slow website / queue saturation tests (instant version)"""
import asyncio

from crawlo.backpressure.strategies import QueueSizeStrategy
from crawlo.backpressure.interfaces import BackpressureStrategyConfig
from crawlo.backpressure import BackpressureController


class PipeQueue:
    async def size(self) -> int:
        return len(self._items)

    def __init__(self, max_size=50):
        self._items = []
        self.max_size = max_size


# ===== Test 1: level progression =====
def test_level_progression():
    q = PipeQueue(30)
    cf = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=3.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=cf))

    async def run():
        levels = set()
        for n in [3, 10, 16, 22, 28, 30]:
            q._items = ["x"] * n
            m = await bc.get_metrics(q)
            levels.add(m.level.value)
        return levels

    lv = asyncio.run(run())
    assert lv == {'normal', 'warning', 'critical', 'full'}
    print("1. Levels: all 4 reached")


# ===== Test 2: delay increases with pressure =====
def test_delay_scale():
    q = PipeQueue(100)
    cf = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=5.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=cf))

    async def run():
        delays = []
        for n in [30, 60, 80, 90, 98]:
            q._items = ["x"] * n
            delays.append(await bc.calculate_delay(q))
        return delays

    d = asyncio.run(run())
    assert d[-1] > d[0] * 5
    assert d[-1] >= 4.0
    print(f"2. Delays: {[f'{x:.1f}' for x in d]} → scales correctly")


# ===== Test 3: recovery from full =====
def test_recovery():
    q = PipeQueue(50)
    cf = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=3.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=cf))

    async def run():
        q._items = ["x"] * 50
        assert (await bc.get_metrics(q)).level.value == 'full'
        # Drain
        q._items = q._items[:10]
        m = await bc.get_metrics(q)
        assert m.level.value == 'normal'
        return m

    m = asyncio.run(run())
    print(f"3. Recovery: level={m.level.value}, util={m.utilization:.0%}")


# ===== Test 4: should_apply vs calculate_delay consistency =====
def test_consistency():
    q = PipeQueue(50)
    cf = BackpressureStrategyConfig(threshold=0.6, base_delay=0.5, max_delay=5.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=cf))

    async def run():
        results = []
        for n in [10, 25, 40, 50]:  # 20%, 50%, 80%, 100%
            q._items = ["x"] * n
            active = await bc.should_apply(q)
            delay = await bc.calculate_delay(q)
            results.append((n / 50, active, delay))
        return results

    r = asyncio.run(run())
    for util, active, delay in r:
        if active:
            assert delay > 0, f"Active BP should have delay > 0 at {util:.0%}"
        else:
            assert delay == 0.0, f"Inactive BP should have delay 0 at {util:.0%}"
    print(f"4. Consistency: {[(f'{u:.0%}', a, f'{d:.1f}') for u, a, d in r]}")


# ===== Test 5: queue in BP → consumer drains → BP releases (state machine) =====
def test_state_machine():
    q = PipeQueue(100)
    cf = BackpressureStrategyConfig(threshold=0.5, base_delay=0.3, max_delay=5.0)
    bc = BackpressureController(strategy=QueueSizeStrategy(config=cf))

    async def run():
        states = []
        sizes = [0, 30, 55, 80, 98, 60, 20, 0]

        for s in sizes:
            q._items = ["x"] * s
            active = await bc.should_apply(q)
            level = (await bc.get_metrics(q)).level.value
            delay = await bc.calculate_delay(q)
            states.append((s, active, level, delay))

        return states

    st = asyncio.run(run())

    # First (empty): no BP
    assert st[0][1] is False
    # Peak (98): CRITICAL/FULL, high delay
    assert st[4][1] is True
    assert st[4][2] in ('critical', 'full')
    assert st[4][3] >= 5.0
    # Last (empty): released
    assert st[-1][1] is False
    assert st[-1][3] == 0.0

    print(f"5. State machine: {[(f'{s}%', a, l, f'{d:.1f}') for s, a, l, d in st]}")


if __name__ == "__main__":
    tests = [
        test_level_progression,
        test_delay_scale,
        test_recovery,
        test_consistency,
        test_state_machine,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")

    print(f"\n{'='*40}")
    print(f"PIPELINE: {passed}/{len(tests)} PASSED")
