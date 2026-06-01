# API 参考

| 项目 | 内容 |
|------|------|
| 版本 | 1.0.0 |
| 关联服务 | quant-qmt-proxy / xtquant-proxy |
| 交互式文档 | REST 启动后访问 `/docs`（Swagger UI）或 `/redoc` |

本文档描述本服务对外暴露的 REST、gRPC、WebSocket 接口。行情/交易底层语义以 [xtquant 官方文档](https://dict.thinktrader.net/nativeApi/start_now.html) 为准。

---

## 1. 通用约定

### 1.1 Base URL

| 协议 | 默认地址 |
|------|----------|
| REST / WebSocket | `http://{APP_HOST}:{APP_PORT}`（默认 `8000`） |
| gRPC | `{GRPC_HOST}:{GRPC_PORT}`（默认 `50051`） |

根路径 `GET /` 返回服务名、版本、运行模式及 `docs_url`。

### 1.2 鉴权

在 `config.yml` 或环境变量 `APP_API_KEYS` 配置了 API Key 时，未携带有效密钥的请求将被拒绝。

| 协议 | 方式 |
|------|------|
| REST | `Authorization: Bearer <api_key>` |
| gRPC | metadata：`authorization: Bearer <api_key>` |
| WebSocket | 查询参数：`?token=<api_key>` |

未配置 `api_keys` 时，鉴权依赖为空，所有请求放行（仅建议用于本地 mock）。

### 1.3 响应包络

REST 成功/业务失败均使用统一 JSON 结构：

```json
{
  "success": true,
  "message": "描述信息",
  "code": 200,
  "timestamp": "2026-06-02T12:00:00.000000",
  "data": {}
}
```

- `success`：业务是否成功
- `code`：HTTP 语义状态码（与 HTTP status 通常一致）
- `data`：载荷；错误时可能含 `error_code`

响应头含 `X-Request-ID` 便于日志关联。

### 1.4 错误

| HTTP | 场景 |
|------|------|
| 401 | 缺少或无效 API Key |
| 404 | 资源不存在（如订阅 ID） |
| 422 | 请求体验证失败 |
| 503 | `/health/ready` 未就绪（dev/prod 下 xtdata 未连接） |
| 500 | 未捕获异常；`app.debug=false` 时 message 为 `Internal server error` |

业务异常（如 `SUBSCRIPTION_NOT_FOUND`）通过 `data.error_code` 返回，HTTP 状态由异常类型映射。

---

## 2. REST — 数据查询

前缀：`/api/v1/data`

### 2.1 `POST /kline-history`

K 线历史。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbols` | string[] | 是 | 标的代码，如 `000001.SZ` |
| `period` | string | 否 | K 线周期，默认 `1d` |
| `start_time` | string | 否 | 起始时间，如 `20240101` |
| `end_time` | string | 否 | 结束时间 |
| `fields` | string[] | 否 | 额外字段 |
| `adjust_type` | string | 否 | 复权：`none` / `front` / `back` 等 |
| `fill_data` | bool | 否 | 是否填充，默认 `true` |

**响应 `data`**：`{ "items": [ ... ] }`，每项为按 symbol 分组的历史序列。

### 2.2 `POST /tick-history`

Tick 历史。请求体字段：`symbols`、`start_time`、`end_time`、`fields`、`adjust_type`。

**响应 `data`**：`{ "items": [ ... ] }`

### 2.3 `POST /full-tick`

全量 Tick 快照。请求体：`symbols`（数组）。

**响应 `data`**：`{ "items": [ ... ] }`

### 2.4 `POST /financial`

财务数据。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbols` | string[] | 是 | 标的 |
| `table_names` | string[] | 是 | 表名，如 `Balance` |
| `start_time` | string | 否 | |
| `end_time` | string | 否 | |

**响应 `data`**：`{ "items": [ ... ] }`

### 2.5 `GET /instrument/{symbol}`

合约详情。

| 查询参数 | 类型 | 默认 | 说明 |
|----------|------|------|------|
| `complete` | bool | `false` | 是否返回完整字段 |

**响应 `data`**：含 `symbol`、`fields` 等。

### 2.6 `POST /trading-calendar`

交易日历。请求体：`market`、`start_time`、`end_time`。

**响应 `data`**：`{ "market", "dates": [...] }`

### 2.7 `POST /index-weight`

指数成分权重。请求体：`index_code`。

**响应 `data`**：`{ "index_code", "components": [...] }`

### 2.8 `GET /sectors`

板块列表，无请求体。

**响应 `data`**：`{ "items": [...] }`

### 2.9 L2 数据

| 路径 | 说明 |
|------|------|
| `POST /l2/quote` | L2 快照 |
| `POST /l2/order` | L2 逐笔委托 |
| `POST /l2/transaction` | L2 逐笔成交 |

请求体：`symbols`、`start_time`、`end_time`。**响应 `data`**：`{ "items": [...] }`

---

## 3. REST — 行情订阅

### 3.1 `POST /subscriptions/quote`

创建持久行情订阅。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `symbols` | string[] | 必填 | 一个或多个标的 |
| `period` | string | `tick` | `tick` 或 K 线周期 |
| `start_time` | string | `""` | |
| `adjust_type` | string | `none` | |
| `count` | int | `0` | 回放条数；`-1` 表示 tick 全历史（tick 周期下会拒绝） |

**响应 `data`（订阅信息）**

| 字段 | 说明 |
|------|------|
| `subscription_id` | 订阅 ID |
| `subscription_type` | `quote` |
| `persistent` | 是否持久 |
| `symbols` / `period` / ... | 创建参数 |
| `redis_stream_key` | Redis 启用且 mirror 时返回，如 `qmt:quote:{id}` |
| `redis_symbol_stream_keys` | `mirror_symbol_streams=true` 时，symbol → stream key 映射 |

### 3.2 `POST /subscriptions/whole-quote`

全推订阅。请求体：`markets`（默认 `["SH","SZ"]`）。`subscription_type` 为 `whole_quote`；需 `xtquant.data.whole_quote_enabled=true`。

### 3.3 `GET /subscriptions`

列出所有订阅。**响应 `data`**：`{ "items": [ ... ] }`

### 3.4 `GET /subscriptions/{subscription_id}`

查询单个订阅；不存在时 404。

### 3.5 `DELETE /subscriptions/{subscription_id}`

删除订阅。**响应 `data`**：`{ "success", "subscription_id" }`

订阅删除后，若启用 Redis，对应 Stream 默认设置 TTL（`grace_ttl_seconds`），见 [Redis Stream 设计](design-redis-stream-market-data.md)。

---

## 4. REST — 交易

前缀：`/api/v1/trading`

### 4.1 `POST /sessions`

创建交易会话。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `account_id` | string | 必填 | 资金账号 |
| `account_type` | string | `STOCK` | 账户类型 |

**响应 `data`（会话信息）**

| 字段 | 说明 |
|------|------|
| `session_id` | 会话 ID |
| `account_id` / `account_type` | 账号信息 |
| `mode` / `environment` | 运行模式 |
| `is_real` | 是否真实环境 |
| `account_kind` / `account_profile` | 账户配置 |
| `orders_enabled` | 是否允许下单 |
| `opened_at_ms` | 创建时间戳 |
| `redis_trading_stream_key` | `mirror_trading_events=true` 且 Redis 启用时返回 |

### 4.2 `GET /sessions/{session_id}`

查询会话；不存在时业务异常。

### 4.3 `DELETE /sessions/{session_id}`

关闭会话并断开 gateway。**响应 `data`**：`{ "success": bool }`

### 4.4 `GET /sessions/{session_id}/asset`

资金资产。

### 4.5 `GET /sessions/{session_id}/positions`

持仓列表。**响应 `data`**：`{ "items": [...] }`

### 4.6 `GET /sessions/{session_id}/orders`

委托列表。

| 查询参数 | 类型 | 默认 | 说明 |
|----------|------|------|------|
| `cancelable_only` | bool | `false` | 仅可撤单 |

### 4.7 `GET /sessions/{session_id}/trades`

成交列表。**响应 `data`**：`{ "items": [...] }`

### 4.8 `POST /sessions/{session_id}/orders`

下单。

| 字段 | 类型 | 说明 |
|------|------|------|
| `stock_code` | string | 标的 |
| `side` | string | `BUY` 或 `SELL` |
| `price_type` | int | xtquant 价格类型 |
| `volume` | int | 数量 |
| `price` | float | 价格 |
| `strategy_name` | string | 策略名 |
| `order_remark` | string | 备注 |

**响应 `data`**：订单对象（含 `order_id` 等）。

### 4.9 `POST /sessions/{session_id}/cancel`

撤单。至少提供以下之一：`order_id`；或 `market` + `order_sysid`。

**响应 `data`**：`{ "success": bool }`

### 4.10 交易事件类型（gRPC `StreamTradingEvents` / Redis Stream）

流式事件统一结构：

```json
{
  "event_time_ms": 1710000000000,
  "event_type": "order_update",
  "payload": { }
}
```

| `event_type` | 说明 |
|--------------|------|
| `account_status` | 账户状态 |
| `asset_update` | 资金变动 |
| `order_update` | 委托变动 |
| `trade_update` | 成交 |
| `position_update` | 持仓变动 |
| `order_error` | 下单错误 |
| `cancel_error` | 撤单错误 |

---

## 5. REST — 健康检查

前缀：`/health`

| 路径 | 说明 |
|------|------|
| `GET /health/` | 基本健康；返回应用名、版本、模式 |
| `GET /health/ready` | 就绪探针。`mock` 恒 200；`dev/prod` 在 xtdata 未连接时 **503** |
| `GET /health/live` | 存活探针 |

**`/health/ready` 的 `data.checks`**

| 键 | 说明 |
|----|------|
| `xtdata` | `status`：`mock` / `connected` / `disconnected` 等；`ready` 决定是否 503 |
| `redis` | `status`：`disabled` / `ok` / `degraded` 等；**不影响**整体 503（策略 A） |
| `redis.metrics` | `publish_total`、`publish_errors`、`circuit_open` 等（Redis 启用时） |

---

## 6. WebSocket

### 6.1 `GET /ws/quote/{subscription_id}`

消费已创建订阅的实时行情。

1. 连接：`ws://host:port/ws/quote/{subscription_id}?token=<api_key>`
2. 服务端发送 `connected`
3. 循环发送 `quote`（行情）或 `heartbeat`（无数据且配置了 `heartbeat_interval`）
4. 错误时发送 `error` 并关闭

**消息类型**

| `type` | 说明 |
|--------|------|
| `connected` | 连接成功，`subscription_id` |
| `quote` | `data` 为行情事件（含 `symbol`、`period`、`payload_type`、`data`） |
| `heartbeat` | 保活 |
| `error` | 错误描述 |

行情事件 `payload_type`：`tick` / `kline`。与 gRPC `StreamQuote` 推送结构一致。

---

## 7. gRPC

Proto 定义见仓库 `proto/` 目录。生成代码：`python scripts/generate_proto.py --mode generate`。

### 7.1 服务一览

| 服务 | Proto | RPC |
|------|-------|-----|
| **Data** | `proto/data.proto` | `GetKlineHistory`、`GetTickHistory`、`GetFullTickSnapshot`、`GetFinancialData`、`GetInstrumentDetail`、`GetTradingCalendar`、`GetIndexWeight`、`GetSectorList`、`GetL2Quote`、`GetL2Order`、`GetL2Transaction`、`StreamQuote`、`StreamWholeQuote` |
| **Trading** | `proto/trading.proto` | `OpenSession`、`CloseSession`、`GetSession`、`GetStockAsset`、`GetStockPositions`、`GetStockOrders`、`GetStockTrades`、`SubmitStockOrder`、`CancelStockOrder`、`StreamTradingEvents` |
| **Health** | `proto/health.proto` | `Check`（标准 gRPC 健康检查） |

### 7.2 鉴权与端口

- Metadata：`authorization: Bearer <api_key>`（与 REST 相同）
- 默认 **明文**端口；生产环境请在前置网关启用 TLS 或内网隔离
- 每个流式 RPC 占用一个 gRPC worker，高并发时请调大 `grpc.max_workers`

### 7.3 与 REST 的对应关系

REST 路径与 gRPC 方法一一对应（订阅/流式除外）。字段命名遵循 proto（snake_case 在 JSON 中一致）。详细 message 定义以 proto 为准。

---

## 8. Redis Stream（可选）

启用 Redis 后，REST 订阅/会话响应会附带 Stream 键名；Go 等异构消费者通过 `XREAD` 广播消费，**不使用** Consumer Group。

| 键模式 | 条件 | 说明 |
|--------|------|------|
| `qmt:quote:{subscription_id}` | 默认 mirror | 按订阅 |
| `qmt:whole:{subscription_id}` | `mirror_whole_quote` | 全推 |
| `qmt:symbol:{symbol}` | `mirror_symbol_streams` | 按标的聚合 |
| `qmt:trading:{session_id}` | `mirror_trading_events` | 交易事件 |

完整设计与配置见 [design-redis-stream-market-data.md](design-redis-stream-market-data.md)。

---

## 9. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-06-02 | 初版：REST / WebSocket / gRPC 全量接口参考 |
