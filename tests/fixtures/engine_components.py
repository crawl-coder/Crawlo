"""P3-4 测试用 Engine 组合组件。"""


class DummyDispatcher:
    def __init__(self, engine):
        self.engine = engine


class DummyDistributed:
    def __init__(self, engine):
        self.engine = engine
