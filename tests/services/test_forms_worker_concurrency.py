"""
Testa que FormsSubmissionWorker spawna múltiplas threads consumidoras e
agrega corretamente as métricas no snapshot.
"""
import time
import threading

import pytest

from sistema.app.services.forms_queue import FormsSubmissionWorker
from sistema.app.core.config import settings


def test_snapshot_aggregates_concurrency_info(monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 3)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)

    worker = FormsSubmissionWorker()
    try:
        worker.start()
        time.sleep(0.3)
        snap = worker.snapshot()
        assert snap["concurrency"] == 3
        assert snap["consumer_threads_alive"] == 3
        assert snap["running"] is True
    finally:
        worker.stop()

    snap_after = worker.snapshot()
    assert snap_after["running"] is False


def test_start_is_idempotent_and_does_not_double_threads(monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 3)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)

    worker = FormsSubmissionWorker()
    try:
        worker.start()
        time.sleep(0.2)
        worker.start()  # segunda chamada — não deve duplicar
        time.sleep(0.1)
        assert worker.consumer_threads_alive_count() == 3
    finally:
        worker.stop()


def test_snapshot_concurrency_field_reflects_setting(monkeypatch):
    """concurrency no snapshot reflete o setting atual."""
    monkeypatch.setattr(settings, "forms_worker_concurrency", 2)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)

    worker = FormsSubmissionWorker()
    try:
        worker.start()
        time.sleep(0.2)
        snap = worker.snapshot()
        assert snap["concurrency"] == 2
    finally:
        worker.stop()


def test_has_alive_consumers_returns_false_before_start():
    worker = FormsSubmissionWorker()
    assert worker.has_alive_consumers() is False


def test_has_alive_consumers_returns_true_after_start(monkeypatch):
    monkeypatch.setattr(settings, "forms_worker_concurrency", 2)
    monkeypatch.setattr(settings, "forms_worker_idle_poll_seconds", 0.05)

    worker = FormsSubmissionWorker()
    try:
        worker.start()
        time.sleep(0.2)
        assert worker.has_alive_consumers() is True
    finally:
        worker.stop()
    assert worker.has_alive_consumers() is False
