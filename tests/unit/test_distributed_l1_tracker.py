"""L1 Unit Tests: TaskTracker (8 cases)"""
import asyncio
import pytest
from crawlo.network.request import Request
from crawlo.queue.task_tracker import TaskTracker, TaskResult


@pytest.fixture(scope="function")
def tracker():
    return TaskTracker("test-worker")


def test_t1_dispatched(tracker):
    asyncio.run(tracker.on_dispatched(Request(url="http://test/1"), "msg-001"))
    assert tracker.processing_count == 1

def test_t2_completed(tracker):
    asyncio.run(tracker.on_dispatched(Request(url="http://test/2"), "msg-002"))
    asyncio.run(tracker.on_completed("msg-002"))
    assert tracker.processing_count == 0
    assert tracker.stats["completed"] == 1

def test_t3_failed_retry(tracker):
    asyncio.run(tracker.on_dispatched(Request(url="http://test/3"), "msg-003"))
    asyncio.run(tracker.on_failed("msg-003", RuntimeError("test"), TaskResult.RETRY))
    assert tracker.stats["retried"] == 1

def test_t4_failed_dead(tracker):
    asyncio.run(tracker.on_dispatched(Request(url="http://test/4"), "msg-004"))
    asyncio.run(tracker.on_failed("msg-004", RuntimeError("fatal"), TaskResult.DEAD_LETTER))
    assert tracker.stats["dead_letter"] == 1

def test_t5_timeout_retry(tracker):
    assert tracker.classify_error(asyncio.TimeoutError()) == TaskResult.RETRY

def test_t6_connection_retry(tracker):
    assert tracker.classify_error(ConnectionError()) == TaskResult.RETRY

def test_t7_unknown_retry(tracker):
    assert tracker.classify_error(ValueError("unknown")) == TaskResult.RETRY

def test_t8_get_processing(tracker):
    asyncio.run(tracker.on_dispatched(Request(url="http://test/proc"), "msg-005"))
    tasks = tracker.get_processing_tasks()
    assert "msg-005" in tasks
