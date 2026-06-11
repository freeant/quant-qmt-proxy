from __future__ import annotations

import time

import pytest

import app.services.xtdata_gateway as xtdata_gateway_module
from app.config import Settings
from app.services.contracts import KlineHistoryQuery, L2Query, TickHistoryQuery, TradingCalendarQuery
from app.services.xtdata_gateway import XtDataGateway
from app.utils.exceptions import DataServiceException


def build_settings(mode: str) -> Settings:
    return Settings(xtquant={"mode": mode, "data": {"qmt_userdata_path": "C:/fake-qmt"}})


@pytest.mark.parametrize(
    "callable_name, kwargs",
    [
        ("get_kline_history", {"query": KlineHistoryQuery(symbols=["000001.SZ"], period="1d")}),
        ("get_tick_history", {"query": TickHistoryQuery(symbols=["000001.SZ"])}),
        ("get_full_tick_snapshot", {"symbols": ["000001.SZ"]}),
    ],
)
def test_real_modes_fail_fast_when_xtdata_is_unavailable(monkeypatch, callable_name: str, kwargs: dict[str, object]):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", False))

    gateway = XtDataGateway(build_settings("dev"))

    with pytest.raises(DataServiceException) as exc:
        getattr(gateway, callable_name)(**kwargs)
    assert exc.value.error_code == "XTDATA_UNAVAILABLE"


def test_mock_mode_keeps_mock_data_paths():
    gateway = XtDataGateway(build_settings("mock"))

    kline = gateway.get_kline_history(KlineHistoryQuery(symbols=["000001.SZ"], period="1d"))
    tick = gateway.get_tick_history(TickHistoryQuery(symbols=["000001.SZ"]))
    snapshot = gateway.get_full_tick_snapshot(["000001.SZ"])

    assert kline[0]["symbol"] == "000001.SZ"
    assert tick[0]["ticks"]
    assert snapshot[0]["tick"]["last_price"] == 100.0


def test_real_mode_connect_attempt_is_single_flight(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: None)
    gateway = XtDataGateway(build_settings("dev"))

    class FakeThread:
        def __init__(self):
            self.started = False

        def is_alive(self):
            return True

    existing_thread = FakeThread()
    gateway._connect_thread = existing_thread

    with gateway._connect_lock:
        thread = gateway._start_connect_thread_locked()

    assert thread is existing_thread


def test_real_mode_connect_respects_retry_cooldown(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: None)
    gateway = XtDataGateway(build_settings("dev"))
    gateway._last_connect_failure_at = time.monotonic()

    def fail_if_called():
        raise AssertionError("should not start a new xtdata connect attempt during cooldown")

    monkeypatch.setattr(gateway, "_configure_xtdata", fail_if_called)

    with gateway._connect_lock:
        thread = gateway._start_connect_thread_locked()

    assert thread is None


class FakeArray:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values

    def __bool__(self):
        raise ValueError("ambiguous truth value")


def test_l2_helpers_accept_empty_array_payloads(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))

    class DummyXtData:
        @staticmethod
        def get_l2_quote(**kwargs):
            return FakeArray([])

        @staticmethod
        def get_l2_order(**kwargs):
            return FakeArray([])

        @staticmethod
        def get_l2_transaction(**kwargs):
            return FakeArray([])

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    query = L2Query(symbols=["000001.SZ"], start_time="", end_time="")
    assert gateway.get_l2_quote(query) == []
    assert gateway.get_l2_order(query) == [{"symbol": "000001.SZ", "orders": []}]
    assert gateway.get_l2_transaction(query) == [
        {"symbol": "000001.SZ", "transactions": []}
    ]


def _build_kline_raw(symbols: list[str], *, columns: list[str] | None = None) -> dict:
    import pandas as pd

    frame = pd.DataFrame(index=symbols, columns=columns or [])
    return {"time": frame, "close": frame.copy()}


def _build_tick_raw(symbols: list[str], *, empty: bool = True) -> dict:
    import numpy as np

    if empty:
        return {symbol: np.array([]) for symbol in symbols}
    dtype = [("time", "i8"), ("lastPrice", "f8")]
    return {symbols[0]: np.array([(1, 10.0)], dtype=dtype)}


def test_kline_history_auto_downloads_when_local_cache_is_empty(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))
    download_calls: list[tuple] = []
    get_calls = {"count": 0}

    class DummyXtData:
        @staticmethod
        def get_market_data(**kwargs):
            get_calls["count"] += 1
            if get_calls["count"] == 1:
                return _build_kline_raw(kwargs["stock_list"], columns=[])
            return _build_kline_raw(kwargs["stock_list"], columns=["20240102"])

        @staticmethod
        def download_history_data2(symbols, period, start_time="", end_time=""):
            download_calls.append((symbols, period, start_time, end_time))

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    items = gateway.get_kline_history(
        KlineHistoryQuery(
            symbols=["000001.SZ"],
            period="1d",
            start_time="20240101",
            end_time="20240102",
        )
    )

    assert download_calls == [(["000001.SZ"], "1d", "20240101", "20240102")]
    assert get_calls["count"] == 2
    assert len(items[0]["bars"]) == 1


def test_kline_history_skips_download_when_auto_download_disabled(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))

    class DummyXtData:
        @staticmethod
        def get_market_data(**kwargs):
            return _build_kline_raw(kwargs["stock_list"], columns=[])

        @staticmethod
        def download_history_data2(*args, **kwargs):
            raise AssertionError("download should not be called when auto_download is false")

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    items = gateway.get_kline_history(
        KlineHistoryQuery(
            symbols=["000001.SZ"],
            period="1d",
            auto_download=False,
        )
    )

    assert items[0]["bars"] == []


def test_tick_history_auto_downloads_when_local_cache_is_empty(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))
    download_calls: list[tuple] = []
    get_calls = {"count": 0}

    class DummyXtData:
        @staticmethod
        def get_market_data(**kwargs):
            get_calls["count"] += 1
            if get_calls["count"] == 1:
                return _build_tick_raw(kwargs["stock_list"], empty=True)
            return _build_tick_raw(kwargs["stock_list"], empty=False)

        @staticmethod
        def download_history_data2(symbols, period, start_time="", end_time=""):
            download_calls.append((symbols, period, start_time, end_time))

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    items = gateway.get_tick_history(
        TickHistoryQuery(
            symbols=["000001.SZ"],
            start_time="20240101093000",
            end_time="20240101093500",
        )
    )

    assert download_calls == [(["000001.SZ"], "tick", "20240101093000", "20240101093500")]
    assert get_calls["count"] == 2
    assert items[0]["ticks"]


def test_kline_history_sanitizes_non_finite_values(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))

    class DummyXtData:
        @staticmethod
        def get_market_data(**kwargs):
            import pandas as pd

            symbol = kwargs["stock_list"][0]
            columns = ["20240102"]
            return {
                "open": pd.DataFrame([[float("nan")]], index=[symbol], columns=columns),
                "high": pd.DataFrame([[float("inf")]], index=[symbol], columns=columns),
                "low": pd.DataFrame([[float("-inf")]], index=[symbol], columns=columns),
                "close": pd.DataFrame([[10.5]], index=[symbol], columns=columns),
                "volume": pd.DataFrame([[100]], index=[symbol], columns=columns),
                "amount": pd.DataFrame([[1000.0]], index=[symbol], columns=columns),
                "settle": pd.DataFrame([[0.0]], index=[symbol], columns=columns),
                "openInterest": pd.DataFrame([[0]], index=[symbol], columns=columns),
                "preClose": pd.DataFrame([[0.0]], index=[symbol], columns=columns),
                "suspendFlag": pd.DataFrame([[0]], index=[symbol], columns=columns),
            }

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    items = gateway.get_kline_history(
        KlineHistoryQuery(
            symbols=["000001.SZ"],
            period="1d",
            auto_download=False,
        )
    )

    bar = items[0]["bars"][0]
    assert bar["open"] is None
    assert bar["high"] is None
    assert bar["low"] is None
    assert bar["close"] == 10.5


def test_trading_calendar_unsupported_maps_to_feature_not_supported(monkeypatch):
    monkeypatch.setattr(XtDataGateway, "_try_initialize", lambda self: setattr(self, "_initialized", True))
    gateway = XtDataGateway(build_settings("dev"))

    class DummyXtData:
        @staticmethod
        def get_trading_calendar(*args, **kwargs):
            raise RuntimeError("function not realize")

    monkeypatch.setattr(xtdata_gateway_module, "xtdata", DummyXtData())

    with pytest.raises(DataServiceException) as exc:
        gateway.get_trading_calendar(TradingCalendarQuery(market="SH", start_time="20240101", end_time="20240131"))
    assert exc.value.error_code == "FEATURE_NOT_SUPPORTED"
