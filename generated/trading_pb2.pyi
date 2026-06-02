import common_pb2 as _common_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SessionInfo(_message.Message):
    __slots__ = ("session_id", "account_id", "account_type", "is_real", "mode", "opened_at_ms", "environment", "account_kind", "orders_enabled", "account_profile")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_REAL_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    OPENED_AT_MS_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_KIND_FIELD_NUMBER: _ClassVar[int]
    ORDERS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_PROFILE_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    account_id: str
    account_type: _common_pb2.SecurityAccountType
    is_real: bool
    mode: str
    opened_at_ms: int
    environment: str
    account_kind: str
    orders_enabled: bool
    account_profile: str
    def __init__(self, session_id: _Optional[str] = ..., account_id: _Optional[str] = ..., account_type: _Optional[_Union[_common_pb2.SecurityAccountType, str]] = ..., is_real: bool = ..., mode: _Optional[str] = ..., opened_at_ms: _Optional[int] = ..., environment: _Optional[str] = ..., account_kind: _Optional[str] = ..., orders_enabled: bool = ..., account_profile: _Optional[str] = ...) -> None: ...

class OpenSessionRequest(_message.Message):
    __slots__ = ("account_id", "account_type")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: _common_pb2.SecurityAccountType
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[_Union[_common_pb2.SecurityAccountType, str]] = ...) -> None: ...

class OpenSessionResponse(_message.Message):
    __slots__ = ("session", "status")
    SESSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    session: SessionInfo
    status: _common_pb2.Status
    def __init__(self, session: _Optional[_Union[SessionInfo, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class CloseSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class CloseSessionResponse(_message.Message):
    __slots__ = ("success", "status")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    status: _common_pb2.Status
    def __init__(self, success: bool = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class GetSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class GetSessionResponse(_message.Message):
    __slots__ = ("session", "status")
    SESSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    session: SessionInfo
    status: _common_pb2.Status
    def __init__(self, session: _Optional[_Union[SessionInfo, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class TradingAccountProfile(_message.Message):
    __slots__ = ("name", "account_id", "account_type", "account_kind", "orders_enabled")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_KIND_FIELD_NUMBER: _ClassVar[int]
    ORDERS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    name: str
    account_id: str
    account_type: _common_pb2.SecurityAccountType
    account_kind: str
    orders_enabled: bool
    def __init__(self, name: _Optional[str] = ..., account_id: _Optional[str] = ..., account_type: _Optional[_Union[_common_pb2.SecurityAccountType, str]] = ..., account_kind: _Optional[str] = ..., orders_enabled: bool = ...) -> None: ...

class ListTradingAccountsResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[TradingAccountProfile]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[TradingAccountProfile, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class GetStockAssetRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class StockAsset(_message.Message):
    __slots__ = ("account_id", "cash", "frozen_cash", "market_value", "total_asset", "fetch_balance")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    CASH_FIELD_NUMBER: _ClassVar[int]
    FROZEN_CASH_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ASSET_FIELD_NUMBER: _ClassVar[int]
    FETCH_BALANCE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    cash: float
    frozen_cash: float
    market_value: float
    total_asset: float
    fetch_balance: float
    def __init__(self, account_id: _Optional[str] = ..., cash: _Optional[float] = ..., frozen_cash: _Optional[float] = ..., market_value: _Optional[float] = ..., total_asset: _Optional[float] = ..., fetch_balance: _Optional[float] = ...) -> None: ...

class GetStockAssetResponse(_message.Message):
    __slots__ = ("asset", "status")
    ASSET_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    asset: StockAsset
    status: _common_pb2.Status
    def __init__(self, asset: _Optional[_Union[StockAsset, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class GetStockPositionsRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class StockPosition(_message.Message):
    __slots__ = ("account_id", "stock_code", "instrument_name", "volume", "can_use_volume", "frozen_volume", "on_road_volume", "yesterday_volume", "open_price", "avg_price", "last_price", "market_value", "profit_rate", "direction", "secu_account")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    CAN_USE_VOLUME_FIELD_NUMBER: _ClassVar[int]
    FROZEN_VOLUME_FIELD_NUMBER: _ClassVar[int]
    ON_ROAD_VOLUME_FIELD_NUMBER: _ClassVar[int]
    YESTERDAY_VOLUME_FIELD_NUMBER: _ClassVar[int]
    OPEN_PRICE_FIELD_NUMBER: _ClassVar[int]
    AVG_PRICE_FIELD_NUMBER: _ClassVar[int]
    LAST_PRICE_FIELD_NUMBER: _ClassVar[int]
    MARKET_VALUE_FIELD_NUMBER: _ClassVar[int]
    PROFIT_RATE_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SECU_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    instrument_name: str
    volume: int
    can_use_volume: int
    frozen_volume: int
    on_road_volume: int
    yesterday_volume: int
    open_price: float
    avg_price: float
    last_price: float
    market_value: float
    profit_rate: float
    direction: str
    secu_account: str
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., instrument_name: _Optional[str] = ..., volume: _Optional[int] = ..., can_use_volume: _Optional[int] = ..., frozen_volume: _Optional[int] = ..., on_road_volume: _Optional[int] = ..., yesterday_volume: _Optional[int] = ..., open_price: _Optional[float] = ..., avg_price: _Optional[float] = ..., last_price: _Optional[float] = ..., market_value: _Optional[float] = ..., profit_rate: _Optional[float] = ..., direction: _Optional[str] = ..., secu_account: _Optional[str] = ...) -> None: ...

class GetStockPositionsResponse(_message.Message):
    __slots__ = ("positions", "status")
    POSITIONS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    positions: _containers.RepeatedCompositeFieldContainer[StockPosition]
    status: _common_pb2.Status
    def __init__(self, positions: _Optional[_Iterable[_Union[StockPosition, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class GetStockOrdersRequest(_message.Message):
    __slots__ = ("session_id", "cancelable_only")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CANCELABLE_ONLY_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    cancelable_only: bool
    def __init__(self, session_id: _Optional[str] = ..., cancelable_only: bool = ...) -> None: ...

class StockOrder(_message.Message):
    __slots__ = ("account_id", "stock_code", "instrument_name", "order_id", "order_sysid", "order_time_ms", "order_type", "order_volume", "price_type", "price", "traded_volume", "traded_price", "order_status_code", "status_msg", "strategy_name", "order_remark", "direction", "offset_flag", "secu_account")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    ORDER_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    ORDER_VOLUME_FIELD_NUMBER: _ClassVar[int]
    PRICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADED_VOLUME_FIELD_NUMBER: _ClassVar[int]
    TRADED_PRICE_FIELD_NUMBER: _ClassVar[int]
    ORDER_STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    STATUS_MSG_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FLAG_FIELD_NUMBER: _ClassVar[int]
    SECU_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    instrument_name: str
    order_id: str
    order_sysid: str
    order_time_ms: int
    order_type: _common_pb2.OrderSide
    order_volume: int
    price_type: _common_pb2.StockPriceType
    price: float
    traded_volume: int
    traded_price: float
    order_status_code: int
    status_msg: str
    strategy_name: str
    order_remark: str
    direction: str
    offset_flag: str
    secu_account: str
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., instrument_name: _Optional[str] = ..., order_id: _Optional[str] = ..., order_sysid: _Optional[str] = ..., order_time_ms: _Optional[int] = ..., order_type: _Optional[_Union[_common_pb2.OrderSide, str]] = ..., order_volume: _Optional[int] = ..., price_type: _Optional[_Union[_common_pb2.StockPriceType, str]] = ..., price: _Optional[float] = ..., traded_volume: _Optional[int] = ..., traded_price: _Optional[float] = ..., order_status_code: _Optional[int] = ..., status_msg: _Optional[str] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ..., direction: _Optional[str] = ..., offset_flag: _Optional[str] = ..., secu_account: _Optional[str] = ...) -> None: ...

class GetStockOrdersResponse(_message.Message):
    __slots__ = ("orders", "status")
    ORDERS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    orders: _containers.RepeatedCompositeFieldContainer[StockOrder]
    status: _common_pb2.Status
    def __init__(self, orders: _Optional[_Iterable[_Union[StockOrder, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class GetStockTradesRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class StockTrade(_message.Message):
    __slots__ = ("account_id", "stock_code", "instrument_name", "order_type", "traded_id", "traded_time_ms", "traded_price", "traded_volume", "traded_amount", "order_id", "order_sysid", "strategy_name", "order_remark", "direction", "offset_flag", "commission", "secu_account")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRADED_ID_FIELD_NUMBER: _ClassVar[int]
    TRADED_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    TRADED_PRICE_FIELD_NUMBER: _ClassVar[int]
    TRADED_VOLUME_FIELD_NUMBER: _ClassVar[int]
    TRADED_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FLAG_FIELD_NUMBER: _ClassVar[int]
    COMMISSION_FIELD_NUMBER: _ClassVar[int]
    SECU_ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    stock_code: str
    instrument_name: str
    order_type: _common_pb2.OrderSide
    traded_id: str
    traded_time_ms: int
    traded_price: float
    traded_volume: int
    traded_amount: float
    order_id: str
    order_sysid: str
    strategy_name: str
    order_remark: str
    direction: str
    offset_flag: str
    commission: float
    secu_account: str
    def __init__(self, account_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., instrument_name: _Optional[str] = ..., order_type: _Optional[_Union[_common_pb2.OrderSide, str]] = ..., traded_id: _Optional[str] = ..., traded_time_ms: _Optional[int] = ..., traded_price: _Optional[float] = ..., traded_volume: _Optional[int] = ..., traded_amount: _Optional[float] = ..., order_id: _Optional[str] = ..., order_sysid: _Optional[str] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ..., direction: _Optional[str] = ..., offset_flag: _Optional[str] = ..., commission: _Optional[float] = ..., secu_account: _Optional[str] = ...) -> None: ...

class GetStockTradesResponse(_message.Message):
    __slots__ = ("trades", "status")
    TRADES_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    trades: _containers.RepeatedCompositeFieldContainer[StockTrade]
    status: _common_pb2.Status
    def __init__(self, trades: _Optional[_Iterable[_Union[StockTrade, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class SubmitStockOrderRequest(_message.Message):
    __slots__ = ("session_id", "stock_code", "side", "price_type", "volume", "price", "strategy_name", "order_remark")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    STOCK_CODE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    stock_code: str
    side: _common_pb2.OrderSide
    price_type: _common_pb2.StockPriceType
    volume: int
    price: float
    strategy_name: str
    order_remark: str
    def __init__(self, session_id: _Optional[str] = ..., stock_code: _Optional[str] = ..., side: _Optional[_Union[_common_pb2.OrderSide, str]] = ..., price_type: _Optional[_Union[_common_pb2.StockPriceType, str]] = ..., volume: _Optional[int] = ..., price: _Optional[float] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ...) -> None: ...

class SubmitStockOrderResponse(_message.Message):
    __slots__ = ("order", "status")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    order: StockOrder
    status: _common_pb2.Status
    def __init__(self, order: _Optional[_Union[StockOrder, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class CancelBySysIdTarget(_message.Message):
    __slots__ = ("market", "order_sysid")
    MARKET_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    market: str
    order_sysid: str
    def __init__(self, market: _Optional[str] = ..., order_sysid: _Optional[str] = ...) -> None: ...

class CancelStockOrderRequest(_message.Message):
    __slots__ = ("session_id", "order_id", "sysid_target")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    SYSID_TARGET_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    order_id: str
    sysid_target: CancelBySysIdTarget
    def __init__(self, session_id: _Optional[str] = ..., order_id: _Optional[str] = ..., sysid_target: _Optional[_Union[CancelBySysIdTarget, _Mapping]] = ...) -> None: ...

class CancelStockOrderResponse(_message.Message):
    __slots__ = ("success", "status")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    status: _common_pb2.Status
    def __init__(self, success: bool = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class StreamTradingEventsRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class AccountStatusEvent(_message.Message):
    __slots__ = ("account_id", "account_type", "status_code")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    account_type: _common_pb2.SecurityAccountType
    status_code: int
    def __init__(self, account_id: _Optional[str] = ..., account_type: _Optional[_Union[_common_pb2.SecurityAccountType, str]] = ..., status_code: _Optional[int] = ...) -> None: ...

class OrderErrorEvent(_message.Message):
    __slots__ = ("account_id", "order_id", "error_id", "error_msg", "strategy_name", "order_remark")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_MSG_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_NAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_REMARK_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    order_id: str
    error_id: int
    error_msg: str
    strategy_name: str
    order_remark: str
    def __init__(self, account_id: _Optional[str] = ..., order_id: _Optional[str] = ..., error_id: _Optional[int] = ..., error_msg: _Optional[str] = ..., strategy_name: _Optional[str] = ..., order_remark: _Optional[str] = ...) -> None: ...

class CancelErrorEvent(_message.Message):
    __slots__ = ("account_id", "order_id", "order_sysid", "error_id", "error_msg")
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_SYSID_FIELD_NUMBER: _ClassVar[int]
    ERROR_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_MSG_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    order_id: str
    order_sysid: str
    error_id: int
    error_msg: str
    def __init__(self, account_id: _Optional[str] = ..., order_id: _Optional[str] = ..., order_sysid: _Optional[str] = ..., error_id: _Optional[int] = ..., error_msg: _Optional[str] = ...) -> None: ...

class TradingEvent(_message.Message):
    __slots__ = ("event_time_ms", "account_status", "asset_update", "order_update", "trade_update", "position_update", "order_error", "cancel_error")
    EVENT_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_STATUS_FIELD_NUMBER: _ClassVar[int]
    ASSET_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ORDER_UPDATE_FIELD_NUMBER: _ClassVar[int]
    TRADE_UPDATE_FIELD_NUMBER: _ClassVar[int]
    POSITION_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ORDER_ERROR_FIELD_NUMBER: _ClassVar[int]
    CANCEL_ERROR_FIELD_NUMBER: _ClassVar[int]
    event_time_ms: int
    account_status: AccountStatusEvent
    asset_update: StockAsset
    order_update: StockOrder
    trade_update: StockTrade
    position_update: StockPosition
    order_error: OrderErrorEvent
    cancel_error: CancelErrorEvent
    def __init__(self, event_time_ms: _Optional[int] = ..., account_status: _Optional[_Union[AccountStatusEvent, _Mapping]] = ..., asset_update: _Optional[_Union[StockAsset, _Mapping]] = ..., order_update: _Optional[_Union[StockOrder, _Mapping]] = ..., trade_update: _Optional[_Union[StockTrade, _Mapping]] = ..., position_update: _Optional[_Union[StockPosition, _Mapping]] = ..., order_error: _Optional[_Union[OrderErrorEvent, _Mapping]] = ..., cancel_error: _Optional[_Union[CancelErrorEvent, _Mapping]] = ...) -> None: ...
