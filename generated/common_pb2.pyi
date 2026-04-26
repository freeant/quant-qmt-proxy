from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class QuotePeriod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    QUOTE_PERIOD_UNSPECIFIED: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_TICK: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1M: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_5M: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_15M: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_30M: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1H: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1D: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1W: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1MON: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1Q: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1HY: _ClassVar[QuotePeriod]
    QUOTE_PERIOD_1Y: _ClassVar[QuotePeriod]

class AdjustType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ADJUST_TYPE_UNSPECIFIED: _ClassVar[AdjustType]
    ADJUST_TYPE_NONE: _ClassVar[AdjustType]
    ADJUST_TYPE_FRONT: _ClassVar[AdjustType]
    ADJUST_TYPE_BACK: _ClassVar[AdjustType]
    ADJUST_TYPE_FRONT_RATIO: _ClassVar[AdjustType]
    ADJUST_TYPE_BACK_RATIO: _ClassVar[AdjustType]

class SecurityAccountType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SECURITY_ACCOUNT_TYPE_UNSPECIFIED: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_FUTURE: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_STOCK: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_CREDIT: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_FUTURE_OPTION: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_STOCK_OPTION: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_HUGANGTONG: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_INCOME_SWAP: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_NEW3BOARD: _ClassVar[SecurityAccountType]
    SECURITY_ACCOUNT_TYPE_SHENGANGTONG: _ClassVar[SecurityAccountType]

class OrderSide(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ORDER_SIDE_UNSPECIFIED: _ClassVar[OrderSide]
    ORDER_SIDE_BUY: _ClassVar[OrderSide]
    ORDER_SIDE_SELL: _ClassVar[OrderSide]

class StockPriceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STOCK_PRICE_TYPE_UNSPECIFIED: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_LATEST_PRICE: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_FIX_PRICE: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_SH_CONVERT_5_CANCEL: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_SH_CONVERT_5_LIMIT: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_PEER_PRICE_FIRST: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_MINE_PRICE_FIRST: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_SZ_INSTBUSI_RESTCANCEL: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_SZ_CONVERT_5_CANCEL: _ClassVar[StockPriceType]
    STOCK_PRICE_TYPE_MARKET_SZ_FULL_OR_CANCEL: _ClassVar[StockPriceType]
QUOTE_PERIOD_UNSPECIFIED: QuotePeriod
QUOTE_PERIOD_TICK: QuotePeriod
QUOTE_PERIOD_1M: QuotePeriod
QUOTE_PERIOD_5M: QuotePeriod
QUOTE_PERIOD_15M: QuotePeriod
QUOTE_PERIOD_30M: QuotePeriod
QUOTE_PERIOD_1H: QuotePeriod
QUOTE_PERIOD_1D: QuotePeriod
QUOTE_PERIOD_1W: QuotePeriod
QUOTE_PERIOD_1MON: QuotePeriod
QUOTE_PERIOD_1Q: QuotePeriod
QUOTE_PERIOD_1HY: QuotePeriod
QUOTE_PERIOD_1Y: QuotePeriod
ADJUST_TYPE_UNSPECIFIED: AdjustType
ADJUST_TYPE_NONE: AdjustType
ADJUST_TYPE_FRONT: AdjustType
ADJUST_TYPE_BACK: AdjustType
ADJUST_TYPE_FRONT_RATIO: AdjustType
ADJUST_TYPE_BACK_RATIO: AdjustType
SECURITY_ACCOUNT_TYPE_UNSPECIFIED: SecurityAccountType
SECURITY_ACCOUNT_TYPE_FUTURE: SecurityAccountType
SECURITY_ACCOUNT_TYPE_STOCK: SecurityAccountType
SECURITY_ACCOUNT_TYPE_CREDIT: SecurityAccountType
SECURITY_ACCOUNT_TYPE_FUTURE_OPTION: SecurityAccountType
SECURITY_ACCOUNT_TYPE_STOCK_OPTION: SecurityAccountType
SECURITY_ACCOUNT_TYPE_HUGANGTONG: SecurityAccountType
SECURITY_ACCOUNT_TYPE_INCOME_SWAP: SecurityAccountType
SECURITY_ACCOUNT_TYPE_NEW3BOARD: SecurityAccountType
SECURITY_ACCOUNT_TYPE_SHENGANGTONG: SecurityAccountType
ORDER_SIDE_UNSPECIFIED: OrderSide
ORDER_SIDE_BUY: OrderSide
ORDER_SIDE_SELL: OrderSide
STOCK_PRICE_TYPE_UNSPECIFIED: StockPriceType
STOCK_PRICE_TYPE_LATEST_PRICE: StockPriceType
STOCK_PRICE_TYPE_FIX_PRICE: StockPriceType
STOCK_PRICE_TYPE_MARKET_SH_CONVERT_5_CANCEL: StockPriceType
STOCK_PRICE_TYPE_MARKET_SH_CONVERT_5_LIMIT: StockPriceType
STOCK_PRICE_TYPE_MARKET_PEER_PRICE_FIRST: StockPriceType
STOCK_PRICE_TYPE_MARKET_MINE_PRICE_FIRST: StockPriceType
STOCK_PRICE_TYPE_MARKET_SZ_INSTBUSI_RESTCANCEL: StockPriceType
STOCK_PRICE_TYPE_MARKET_SZ_CONVERT_5_CANCEL: StockPriceType
STOCK_PRICE_TYPE_MARKET_SZ_FULL_OR_CANCEL: StockPriceType

class Status(_message.Message):
    __slots__ = ("code", "message", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    code: int
    message: str
    details: _containers.ScalarMap[str, str]
    def __init__(self, code: _Optional[int] = ..., message: _Optional[str] = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...
