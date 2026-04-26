import common_pb2 as _common_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class KlineHistoryRequest(_message.Message):
    __slots__ = ("symbols", "period", "start_time", "end_time", "fields", "adjust_type", "fill_data")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    ADJUST_TYPE_FIELD_NUMBER: _ClassVar[int]
    FILL_DATA_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    period: _common_pb2.QuotePeriod
    start_time: str
    end_time: str
    fields: _containers.RepeatedScalarFieldContainer[str]
    adjust_type: _common_pb2.AdjustType
    fill_data: bool
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., period: _Optional[_Union[_common_pb2.QuotePeriod, str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., fields: _Optional[_Iterable[str]] = ..., adjust_type: _Optional[_Union[_common_pb2.AdjustType, str]] = ..., fill_data: bool = ...) -> None: ...

class KlineBar(_message.Message):
    __slots__ = ("time_ms", "open", "high", "low", "close", "volume", "amount", "settle", "open_interest", "pre_close", "suspend_flag")
    TIME_MS_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    SETTLE_FIELD_NUMBER: _ClassVar[int]
    OPEN_INTEREST_FIELD_NUMBER: _ClassVar[int]
    PRE_CLOSE_FIELD_NUMBER: _ClassVar[int]
    SUSPEND_FLAG_FIELD_NUMBER: _ClassVar[int]
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    settle: float
    open_interest: int
    pre_close: float
    suspend_flag: int
    def __init__(self, time_ms: _Optional[int] = ..., open: _Optional[float] = ..., high: _Optional[float] = ..., low: _Optional[float] = ..., close: _Optional[float] = ..., volume: _Optional[int] = ..., amount: _Optional[float] = ..., settle: _Optional[float] = ..., open_interest: _Optional[int] = ..., pre_close: _Optional[float] = ..., suspend_flag: _Optional[int] = ...) -> None: ...

class KlineSeries(_message.Message):
    __slots__ = ("symbol", "bars", "fields")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    BARS_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    bars: _containers.RepeatedCompositeFieldContainer[KlineBar]
    fields: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, symbol: _Optional[str] = ..., bars: _Optional[_Iterable[_Union[KlineBar, _Mapping]]] = ..., fields: _Optional[_Iterable[str]] = ...) -> None: ...

class KlineHistoryResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[KlineSeries]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[KlineSeries, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class TickHistoryRequest(_message.Message):
    __slots__ = ("symbols", "start_time", "end_time", "fields", "adjust_type")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    ADJUST_TYPE_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    fields: _containers.RepeatedScalarFieldContainer[str]
    adjust_type: _common_pb2.AdjustType
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ..., fields: _Optional[_Iterable[str]] = ..., adjust_type: _Optional[_Union[_common_pb2.AdjustType, str]] = ...) -> None: ...

class TickRecord(_message.Message):
    __slots__ = ("time_ms", "last_price", "open", "high", "low", "last_close", "amount", "volume", "pvolume", "open_int", "stock_status", "last_settlement_price", "ask_price", "bid_price", "ask_vol", "bid_vol", "transaction_num")
    TIME_MS_FIELD_NUMBER: _ClassVar[int]
    LAST_PRICE_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    HIGH_FIELD_NUMBER: _ClassVar[int]
    LOW_FIELD_NUMBER: _ClassVar[int]
    LAST_CLOSE_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    PVOLUME_FIELD_NUMBER: _ClassVar[int]
    OPEN_INT_FIELD_NUMBER: _ClassVar[int]
    STOCK_STATUS_FIELD_NUMBER: _ClassVar[int]
    LAST_SETTLEMENT_PRICE_FIELD_NUMBER: _ClassVar[int]
    ASK_PRICE_FIELD_NUMBER: _ClassVar[int]
    BID_PRICE_FIELD_NUMBER: _ClassVar[int]
    ASK_VOL_FIELD_NUMBER: _ClassVar[int]
    BID_VOL_FIELD_NUMBER: _ClassVar[int]
    TRANSACTION_NUM_FIELD_NUMBER: _ClassVar[int]
    time_ms: int
    last_price: float
    open: float
    high: float
    low: float
    last_close: float
    amount: float
    volume: int
    pvolume: int
    open_int: int
    stock_status: int
    last_settlement_price: float
    ask_price: _containers.RepeatedScalarFieldContainer[float]
    bid_price: _containers.RepeatedScalarFieldContainer[float]
    ask_vol: _containers.RepeatedScalarFieldContainer[int]
    bid_vol: _containers.RepeatedScalarFieldContainer[int]
    transaction_num: int
    def __init__(self, time_ms: _Optional[int] = ..., last_price: _Optional[float] = ..., open: _Optional[float] = ..., high: _Optional[float] = ..., low: _Optional[float] = ..., last_close: _Optional[float] = ..., amount: _Optional[float] = ..., volume: _Optional[int] = ..., pvolume: _Optional[int] = ..., open_int: _Optional[int] = ..., stock_status: _Optional[int] = ..., last_settlement_price: _Optional[float] = ..., ask_price: _Optional[_Iterable[float]] = ..., bid_price: _Optional[_Iterable[float]] = ..., ask_vol: _Optional[_Iterable[int]] = ..., bid_vol: _Optional[_Iterable[int]] = ..., transaction_num: _Optional[int] = ...) -> None: ...

class TickSeries(_message.Message):
    __slots__ = ("symbol", "ticks", "fields")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TICKS_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    ticks: _containers.RepeatedCompositeFieldContainer[TickRecord]
    fields: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, symbol: _Optional[str] = ..., ticks: _Optional[_Iterable[_Union[TickRecord, _Mapping]]] = ..., fields: _Optional[_Iterable[str]] = ...) -> None: ...

class TickHistoryResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[TickSeries]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[TickSeries, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class FullTickSnapshotRequest(_message.Message):
    __slots__ = ("symbols",)
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, symbols: _Optional[_Iterable[str]] = ...) -> None: ...

class FullTickSnapshot(_message.Message):
    __slots__ = ("symbol", "tick")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TICK_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    tick: TickRecord
    def __init__(self, symbol: _Optional[str] = ..., tick: _Optional[_Union[TickRecord, _Mapping]] = ...) -> None: ...

class FullTickSnapshotResponse(_message.Message):
    __slots__ = ("snapshots", "status")
    SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    snapshots: _containers.RepeatedCompositeFieldContainer[FullTickSnapshot]
    status: _common_pb2.Status
    def __init__(self, snapshots: _Optional[_Iterable[_Union[FullTickSnapshot, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class QuoteStreamRequest(_message.Message):
    __slots__ = ("symbols", "period", "start_time", "adjust_type", "count")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    ADJUST_TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    period: _common_pb2.QuotePeriod
    start_time: str
    adjust_type: _common_pb2.AdjustType
    count: int
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., period: _Optional[_Union[_common_pb2.QuotePeriod, str]] = ..., start_time: _Optional[str] = ..., adjust_type: _Optional[_Union[_common_pb2.AdjustType, str]] = ..., count: _Optional[int] = ...) -> None: ...

class WholeQuoteStreamRequest(_message.Message):
    __slots__ = ("markets",)
    MARKETS_FIELD_NUMBER: _ClassVar[int]
    markets: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, markets: _Optional[_Iterable[str]] = ...) -> None: ...

class QuoteEvent(_message.Message):
    __slots__ = ("symbol", "period", "event_time_ms", "tick", "kline")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    EVENT_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    TICK_FIELD_NUMBER: _ClassVar[int]
    KLINE_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    period: str
    event_time_ms: int
    tick: TickRecord
    kline: KlineBar
    def __init__(self, symbol: _Optional[str] = ..., period: _Optional[str] = ..., event_time_ms: _Optional[int] = ..., tick: _Optional[_Union[TickRecord, _Mapping]] = ..., kline: _Optional[_Union[KlineBar, _Mapping]] = ...) -> None: ...

class FinancialDataRequest(_message.Message):
    __slots__ = ("symbols", "table_names", "start_time", "end_time")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    TABLE_NAMES_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    table_names: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., table_names: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class FinancialDataRow(_message.Message):
    __slots__ = ("fields",)
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.ScalarMap[str, str]
    def __init__(self, fields: _Optional[_Mapping[str, str]] = ...) -> None: ...

class FinancialTable(_message.Message):
    __slots__ = ("symbol", "table_name", "columns", "rows")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TABLE_NAME_FIELD_NUMBER: _ClassVar[int]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    ROWS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    table_name: str
    columns: _containers.RepeatedScalarFieldContainer[str]
    rows: _containers.RepeatedCompositeFieldContainer[FinancialDataRow]
    def __init__(self, symbol: _Optional[str] = ..., table_name: _Optional[str] = ..., columns: _Optional[_Iterable[str]] = ..., rows: _Optional[_Iterable[_Union[FinancialDataRow, _Mapping]]] = ...) -> None: ...

class FinancialDataResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[FinancialTable]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[FinancialTable, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class InstrumentDetailRequest(_message.Message):
    __slots__ = ("symbol", "complete")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    COMPLETE_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    complete: bool
    def __init__(self, symbol: _Optional[str] = ..., complete: bool = ...) -> None: ...

class InstrumentDetail(_message.Message):
    __slots__ = ("symbol", "fields")
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    fields: _containers.ScalarMap[str, str]
    def __init__(self, symbol: _Optional[str] = ..., fields: _Optional[_Mapping[str, str]] = ...) -> None: ...

class InstrumentDetailResponse(_message.Message):
    __slots__ = ("detail", "status")
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    detail: InstrumentDetail
    status: _common_pb2.Status
    def __init__(self, detail: _Optional[_Union[InstrumentDetail, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class TradingCalendarRequest(_message.Message):
    __slots__ = ("market", "start_time", "end_time")
    MARKET_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    market: str
    start_time: str
    end_time: str
    def __init__(self, market: _Optional[str] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class TradingCalendarResponse(_message.Message):
    __slots__ = ("market", "dates", "status")
    MARKET_FIELD_NUMBER: _ClassVar[int]
    DATES_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    market: str
    dates: _containers.RepeatedScalarFieldContainer[str]
    status: _common_pb2.Status
    def __init__(self, market: _Optional[str] = ..., dates: _Optional[_Iterable[str]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class IndexWeightRequest(_message.Message):
    __slots__ = ("index_code",)
    INDEX_CODE_FIELD_NUMBER: _ClassVar[int]
    index_code: str
    def __init__(self, index_code: _Optional[str] = ...) -> None: ...

class IndexComponent(_message.Message):
    __slots__ = ("symbol", "weight")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    weight: float
    def __init__(self, symbol: _Optional[str] = ..., weight: _Optional[float] = ...) -> None: ...

class IndexWeightResponse(_message.Message):
    __slots__ = ("index_code", "components", "status")
    INDEX_CODE_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    index_code: str
    components: _containers.RepeatedCompositeFieldContainer[IndexComponent]
    status: _common_pb2.Status
    def __init__(self, index_code: _Optional[str] = ..., components: _Optional[_Iterable[_Union[IndexComponent, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class SectorInfo(_message.Message):
    __slots__ = ("sector_name", "symbols")
    SECTOR_NAME_FIELD_NUMBER: _ClassVar[int]
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    sector_name: str
    symbols: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, sector_name: _Optional[str] = ..., symbols: _Optional[_Iterable[str]] = ...) -> None: ...

class SectorListResponse(_message.Message):
    __slots__ = ("sectors", "status")
    SECTORS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    sectors: _containers.RepeatedCompositeFieldContainer[SectorInfo]
    status: _common_pb2.Status
    def __init__(self, sectors: _Optional[_Iterable[_Union[SectorInfo, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class L2QuoteRequest(_message.Message):
    __slots__ = ("symbols", "start_time", "end_time")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class L2Quote(_message.Message):
    __slots__ = ("symbol", "quote")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    QUOTE_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    quote: TickRecord
    def __init__(self, symbol: _Optional[str] = ..., quote: _Optional[_Union[TickRecord, _Mapping]] = ...) -> None: ...

class L2QuoteResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[L2Quote]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[L2Quote, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class L2OrderRequest(_message.Message):
    __slots__ = ("symbols", "start_time", "end_time")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class L2OrderRecord(_message.Message):
    __slots__ = ("time_ms", "price", "volume", "entrust_no", "entrust_type", "entrust_direction")
    TIME_MS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    ENTRUST_NO_FIELD_NUMBER: _ClassVar[int]
    ENTRUST_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENTRUST_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    time_ms: int
    price: float
    volume: int
    entrust_no: int
    entrust_type: int
    entrust_direction: int
    def __init__(self, time_ms: _Optional[int] = ..., price: _Optional[float] = ..., volume: _Optional[int] = ..., entrust_no: _Optional[int] = ..., entrust_type: _Optional[int] = ..., entrust_direction: _Optional[int] = ...) -> None: ...

class L2OrderSeries(_message.Message):
    __slots__ = ("symbol", "orders")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    ORDERS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    orders: _containers.RepeatedCompositeFieldContainer[L2OrderRecord]
    def __init__(self, symbol: _Optional[str] = ..., orders: _Optional[_Iterable[_Union[L2OrderRecord, _Mapping]]] = ...) -> None: ...

class L2OrderResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[L2OrderSeries]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[L2OrderSeries, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...

class L2TransactionRequest(_message.Message):
    __slots__ = ("symbols", "start_time", "end_time")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, symbols: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class L2TransactionRecord(_message.Message):
    __slots__ = ("time_ms", "price", "volume", "amount", "trade_index", "buy_no", "sell_no", "trade_type", "trade_flag")
    TIME_MS_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    TRADE_INDEX_FIELD_NUMBER: _ClassVar[int]
    BUY_NO_FIELD_NUMBER: _ClassVar[int]
    SELL_NO_FIELD_NUMBER: _ClassVar[int]
    TRADE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRADE_FLAG_FIELD_NUMBER: _ClassVar[int]
    time_ms: int
    price: float
    volume: int
    amount: float
    trade_index: int
    buy_no: int
    sell_no: int
    trade_type: int
    trade_flag: int
    def __init__(self, time_ms: _Optional[int] = ..., price: _Optional[float] = ..., volume: _Optional[int] = ..., amount: _Optional[float] = ..., trade_index: _Optional[int] = ..., buy_no: _Optional[int] = ..., sell_no: _Optional[int] = ..., trade_type: _Optional[int] = ..., trade_flag: _Optional[int] = ...) -> None: ...

class L2TransactionSeries(_message.Message):
    __slots__ = ("symbol", "transactions")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    TRANSACTIONS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    transactions: _containers.RepeatedCompositeFieldContainer[L2TransactionRecord]
    def __init__(self, symbol: _Optional[str] = ..., transactions: _Optional[_Iterable[_Union[L2TransactionRecord, _Mapping]]] = ...) -> None: ...

class L2TransactionResponse(_message.Message):
    __slots__ = ("items", "status")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[L2TransactionSeries]
    status: _common_pb2.Status
    def __init__(self, items: _Optional[_Iterable[_Union[L2TransactionSeries, _Mapping]]] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ...) -> None: ...
