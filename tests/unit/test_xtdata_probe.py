from __future__ import annotations

import app.services.xtdata_probe as xtdata_probe_module
from app.config import Settings
from app.services.xtdata_probe import ensure_xtdata_probe_loop
from app.services.xtdata_gateway import XtDataGateway


def build_settings(mode: str) -> Settings:
    return Settings(xtquant={"mode": mode, "data": {"qmt_userdata_path": "C:/fake-qmt"}})


def test_probe_loop_starts_once_for_dev_mode(monkeypatch):
    monkeypatch.setattr(xtdata_probe_module, "_PROBE_THREAD", None)
    gateway = XtDataGateway(build_settings("mock"))
    settings = build_settings("dev")
    settings.xtquant.data.probe_interval_seconds = 3600

    ensure_xtdata_probe_loop(gateway, settings)
    first_thread = xtdata_probe_module._PROBE_THREAD
    ensure_xtdata_probe_loop(gateway, settings)

    assert first_thread is not None
    assert xtdata_probe_module._PROBE_THREAD is first_thread
    assert first_thread.is_alive()


def test_probe_loop_disabled_when_interval_is_zero(monkeypatch):
    monkeypatch.setattr(xtdata_probe_module, "_PROBE_THREAD", None)
    gateway = XtDataGateway(build_settings("mock"))
    settings = build_settings("dev")
    settings.xtquant.data.probe_interval_seconds = 0

    ensure_xtdata_probe_loop(gateway, settings)

    assert xtdata_probe_module._PROBE_THREAD is None
