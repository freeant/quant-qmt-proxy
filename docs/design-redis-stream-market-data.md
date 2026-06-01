# 行情 Redis Stream 广播 — 设计文档

| 项目 | 内容 |
|------|------|
| 状态 | **Approved（评审通过）** |
| 版本 | 0.2 |
| 日期 | 2026-06-01 |
| 关联服务 | quant-qmt-proxy / xtquant-proxy |
| 上一版本 | [0.1 初稿评审说明见 §19](#19-修订记录) |

---

## 1. 背景与目标

### 1.1 背景

当前行情推流路径为：

`xtdata 回调` → `XtDataSubscriptionHub._fanout` → 进程内 `queue.Queue` → **gRPC 流** / **WebSocket**。

该模型适合与本服务保持长连接的 Python 或同源客户端，但对 **局域网内异构语言系统**（如 Go 策略、风控、监控）不够友好：需要实现 gRPC/WebSocket 客户端、处理重连与鉴权，并与 Python 代理进程耦合。

本机或局域网已具备 **Redis**（默认 `127.0.0.1:6379`），拟将其作为 **可选行情旁路（sidecar bus）**，在不替换现有 WS/gRPC 的前提下，向多个消费者 **广播** 同一份标准化行情事件。

### 1.2 目标

| 编号 | 目标 |
|------|------|
| G1 | 局域网内 Go 等消费者通过 Redis Stream 接收行情，无需连接 proxy 的 gRPC/WebSocket 数据面 |
| G2 | **广播语义**：每个消费者独立读取，均能收到订阅范围内的全量事件（非竞争消费） |
| G3 | 消息体与现有 WebSocket `quote` 事件载荷对齐，降低字段歧义 |
| G4 | 与现有 `subscription_id` 生命周期一致：创建订阅 → 写 Stream → 删除订阅 → 停止写入并可清理 Stream |
| G5 | Redis 为 **可选依赖**：关闭或故障时，不影响 WS/gRPC 主路径 |
| G6 | 支持 `mock` 模式写入假数据，便于 Go 侧联调 |

### 1.3 非目标（本期不做）

- 用 Redis **替代** 进程内 `queue` 或 WS/gRPC 主路径
- 多实例 proxy 共享同一 QMT 订阅（xtquant 仍约束为 **单写者 / 单进程**）
- 使用单个 Consumer Group 多成员实现 **竞争消费**（与广播需求相反）
- 交易事件（`TradingEventHub`）写入 Redis（可二期单独设计）
- Redis TLS、Cluster、Sentinel（一期仅单节点 URL）
- 按 `symbol` 建全局 Stream（与 REST 订阅模型不一致，二期再评估）
- 消息 gzip 压缩（一期明文 JSON；whole quote 默认不写 Redis）

---

## 2. 需求摘要

| 维度 | 约定 |
|------|------|
| 消费者 | 局域网内其他语言（如 Go） |
| 分发语义 | **广播**（多读者各自游标，各读全量） |
| Redis | 本地或局域网主机，默认端口 6379 |
| 控制面 | proxy REST 创建/删除订阅；响应含 `redis_stream_key`（启用 Redis 时） |
| 数据面 | Redis Stream `XADD` / `XREAD` |

---

## 3. 架构

### 3.1 逻辑架构

```text
┌─────────────────────────────────────────────────────────────────┐
│  Windows 主机（QMT + quant-qmt-proxy 单实例）                      │
│                                                                 │
│  xtdata ──callback──► XtDataSubscriptionHub._fanout             │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│        queue (WS)     queue (gRPC)    RedisStreamSink (可选)     │
│              │               │               │                  │
│              ▼               ▼               ▼                  │
│         WebSocket        gRPC Stream    XADD ───────────────┼──┐
└──────────────────────────────────────────────────────────────┘  │
                                                                  │
              局域网 Redis :6379（可与 proxy 同机或同网段主机）        │
                              │                                   │
         ┌────────────────────┼────────────────────┐              │
         ▼                    ▼                    ▼              │
    Go 策略 A              Go 策略 B           其它服务         ◄┘
    XREAD 独立 last_id     XREAD 独立 last_id
```

### 3.2 角色划分

| 角色 | 职责 |
|------|------|
| **Producer** | 仅 proxy 进程内 `RedisStreamSink`，在 `_fanout` 中调用（与 queue 写入顺序一致） |
| **Control Plane** | 现有 REST：`POST/DELETE /api/v1/data/subscriptions/*` |
| **Consumer** | 局域网 Go 等：REST 拿 `subscription_id` + `redis_stream_key`，再 `XREAD` |
| **Redis** | 持久化短窗口流；不负责订阅 xtquant |

### 3.3 与现有组件关系

- **挂载点**：`XtDataSubscriptionHub._fanout(subscription_id, event)` 在写入各 `consumer_queue` **之后**调用 Sink（与内存 fan-out 顺序一致：先保证 WS/gRPC，再写 Redis）。
- **不变**：`UiSubscriptionService`、WebSocket、`DataGrpcService.StreamQuote` 行为保持不变。
- **新增**：配置块 `redis` + 模块 `app/services/redis_stream_sink.py`。

### 3.4 持久订阅 vs gRPC 临时订阅

| 类型 | 创建方式 | `persistent` | 默认写 Redis |
|------|----------|--------------|--------------|
| 持久订阅 | REST `POST /subscriptions/quote` | `true` | **是**（`redis.enabled=true`） |
| 临时订阅 | gRPC `StreamQuote` / `StreamWholeQuote` | `false` | **否**（`mirror_ephemeral: false`） |

临时流结束时会 `delete_subscription`；若 `mirror_ephemeral=true`，同样 `XADD` 并在删除时清理 Stream（易制造大量短命键，**默认关闭**）。

---

## 4. Stream 命名与生命周期

### 4.1 Stream Key 规则

前缀可配置，默认 `qmt`：

| 订阅类型 | Stream Key | 示例 |
|----------|------------|------|
| 普通行情 `quote` | `{prefix}:quote:{subscription_id}` | `qmt:quote:quote_a1b2c3d4e5f6` |
| 全推 `whole_quote` | `{prefix}:whole:{subscription_id}` | `qmt:whole:whole_f6e5d4c3b2a1` |

`subscription_id` 与 REST 返回、WebSocket 路径参数一致。**一个订阅一个 Stream**；多标的共用同一 Stream，靠 `event.symbol` 区分（见 §4.4）。

**REST 响应（Phase 1）**：当 `redis.enabled=true` 时，创建/查询订阅返回：

```json
{
  "subscription_id": "quote_xxx",
  "redis_stream_key": "qmt:quote:quote_xxx",
  ...
}
```

避免 Go 侧手工拼键错误。

### 4.2 生命周期

```text
POST /subscriptions/quote
    → Hub 创建 SubscriptionRecord
    → 响应含 redis_stream_key（若 Redis 启用）
    → 首条行情 XADD 时自动创建 Stream

行情事件
    → _fanout → queue + XADD（带 MAXLEN）

DELETE /subscriptions/{id}
    → active=false，停止 XADD
    → grace_ttl_seconds > 0：EXPIRE（延迟删键）
    → 否则且 delete_stream_on_unsubscribe：DEL
```

### 4.3 删除策略（评审决议）

| 配置 | 行为 | 默认 |
|------|------|------|
| `delete_stream_on_unsubscribe` | `DELETE` 时立即 `DEL` stream | `false` |
| `grace_ttl_seconds` | `DELETE` 时 `EXPIRE key grace_ttl_seconds`，仅停写 | **`60`** |
| 二者同时 | 优先 `grace_ttl_seconds`（>0 时 EXPIRE，不立即 DEL） | — |

**理由**：多 Go 读者广播时，一方 `DELETE` 不应立刻使其他读者 `XREAD` 失败；60s 窗口便于短时重连补读。若需立即释放内存，设 `grace_ttl_seconds: 0` 且 `delete_stream_on_unsubscribe: true`。

**协调**：文档约定由**一个**控制进程负责 `DELETE`；只读消费者仅 `XREAD`，不删订阅。

### 4.4 多标的订阅

一次 `POST /subscriptions/quote` 可含多个 `symbols`，对应**一个** `subscription_id`、**一个** Stream。每条 `XADD` 的 `event.symbol` 标识标的，Go 侧按 symbol 过滤即可。

### 4.5 MAXLEN 与内存

```text
XADD key MAXLEN ~ <maxlen> * payload <json>
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `maxlen` | `2000` | 与 `xtquant.data.max_queue_size` 同量级 |
| 近似 `~` | 启用 | 降低 Redis CPU |

**whole quote**：`mirror_whole_quote: false`（默认）；若开启，使用 `whole_quote_maxlen`（如 5000）。

---

## 5. 消息格式

### 5.1 Redis 层

| Field | 值 |
|-------|-----|
| `payload` | UTF-8 JSON 字符串（**完整信封**，见 §5.2） |

Stream Entry ID 由 Redis 生成；消费者以 ID 作为游标。

### 5.2 JSON 信封（规范载荷）

WebSocket 推送为 `{ "type": "quote", "data": <event> }`。Redis **`payload` 字段为下列信封对象**（不是裸 `data`）：

```json
{
  "schema_version": 1,
  "source": "xtquant-proxy",
  "subscription_id": "quote_a1b2c3d4e5f67890",
  "subscription_type": "quote",
  "mode": "dev",
  "published_at_ms": 1717234567890,
  "event": {
    "symbol": "000001.SZ",
    "period": "tick",
    "event_time_ms": 1717234567880,
    "payload_type": "tick",
    "data": {
      "last_price": 12.34,
      "volume": 1000
    }
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `schema_version` | int | 是 | 当前 `1` |
| `source` | string | 是 | `xtquant-proxy` |
| `subscription_id` | string | 是 | 与 Stream 键一致 |
| `subscription_type` | string | 是 | `quote` \| `whole_quote` |
| `mode` | string | 是 | `mock` \| `dev` \| `prod` |
| `published_at_ms` | int | 是 | proxy 写入 Redis 时刻（epoch ms） |
| `event` | object | 是 | 与 `_fanout` 入参相同（等同 WS 的 `data`） |

**tick / kline**：`event.payload_type` 为 `tick` 或 `kline`；`event.data` 与 `XtDataGateway` 归一化结果一致。

### 5.3 版本演进

- 仅增字段：保持 `schema_version`，消费者忽略未知字段。
- 删改字段：`schema_version` + 1。

### 5.4 控制类消息（Phase 2，可选）

WebSocket 有 `connected` / `heartbeat` / `error`。Redis 一期**不**镜像心跳；若 Go 需要就绪信号，二期可在创建订阅后 `XADD` 一条 `event.payload_type: "subscription_ready"`。

---

## 6. 广播语义与消费模式

### 6.1 原则

- **禁止** 多 Go 服务共用一个 Consumer Group 名称（竞争消费）。
- **推荐** 每进程独立 `last_id`，对同一 Stream `XREAD`。

### 6.2 独立游标 `XREAD`

| 场景 | `last_id` | 说明 |
|------|-----------|------|
| 仅消费新行情 | `$` | 从命令发起后新条目开始；**不**含创建订阅前的 tick |
| 窗口内回溯 | `0-0` 或 `XRANGE` | 受 `MAXLEN` 限制 |
| 断线恢复 | 上次成功处理的 ID | 持久化到本地文件/Redis |

**推荐顺序**：

```text
1. POST 创建订阅，读取 redis_stream_key
2. 立即 XREAD BLOCK（last_id="$"）进入循环
3. 若需要最近 N 条：先 XRANGE key -N +，再 XREAD 跟进
```

### 6.3 Go 示例（独立游标）

见 [附录 A](#17-附录-ago-消费者最小示例)。

### 6.4 与 Pub/Sub 对比

| 能力 | Stream + 独立 XREAD | Pub/Sub |
|------|---------------------|---------|
| 广播 | 是 | 是 |
| 断线补读 | MAXLEN 窗口内可以 | 否 |

---

## 7. Producer 设计（proxy 侧）

### 7.1 模块职责

```text
RedisStreamSink
  - publish(subscription_id, subscription_type, record, event) -> None
  - on_subscription_deleted(subscription_id, subscription_type) -> None
  - build_stream_key(subscription_id, subscription_type) -> str
  - ping() -> bool
  - close() -> None
```

`XtDataSubscriptionHub` 持有 `sink: RedisStreamSink | None`；通过 `dependencies` 注入，与现有 Gateway 模式一致。

### 7.2 写入条件

同时满足才 `XADD`：

1. `redis.enabled=true`
2. `record.persistent=true` **或** `redis.mirror_ephemeral=true`
3. `subscription_type == whole_quote` 时还需 `redis.mirror_whole_quote=true`
4. `mode == mock` 时还需 `redis.mirror_mock=true`

### 7.3 线程与性能

| 项 | 方案 |
|----|------|
| 回调线程 | xtdata 线程；**禁止**阻塞重试 |
| 写入 | 单次 `XADD`，socket 超时 ≤ `write_timeout_ms`（默认 50ms） |
| 背压 | `fail_open=true`：失败丢弃 Redis 写入，不影响 queue |
| 连接 | `redis-py` 连接池，`decode_responses=True` |

### 7.4 失败策略（fail-open）

| 场景 | 行为 |
|------|------|
| Redis 不可用 | warning 日志；WS/gRPC 正常 |
| 单条超时/失败 | 丢弃该条 |
| 连续失败 | Phase 2：短时熔断 |

### 7.5 mock 模式

`mirror_mock=true`（默认）时 mock 行情写入 Redis，供 Go 无 QMT 联调。

---

## 8. 控制面流程（Go 消费者）

```text
1. POST /api/v1/data/subscriptions/quote  (+ Bearer api_key)
2. ← subscription_id, redis_stream_key
3. XREAD BLOCK redis_stream_key
4. 退出时：由协调进程 DELETE 订阅（其它读者仅停 XREAD）
```

全推：`POST /subscriptions/whole-quote` → `qmt:whole:{id}`，且需 `whole_quote_enabled` 与 `mirror_whole_quote`。

### 8.1 鉴权

| 通道 | 方式 |
|------|------|
| REST | `Authorization: Bearer` |
| Redis | 网络隔离 + `requirepass` / ACL 只读账号；**一期不在 Redis 层鉴权** |

密码统一通过 **`REDIS_URL`**，例如 `redis://:password@192.168.1.10:6379/0`（评审决议）。

---

## 9. 配置项

```yaml
redis:
  enabled: false
  url: "redis://127.0.0.1:6379/0"      # 跨机时改为局域网 IP；密码写在 URL
  stream_prefix: "qmt"
  maxlen: 2000
  connect_timeout_seconds: 2
  write_timeout_ms: 50
  fail_open: true
  delete_stream_on_unsubscribe: false
  grace_ttl_seconds: 60                 # 0 且 delete=true 时立即 DEL
  mirror_mock: true
  mirror_ephemeral: false               # gRPC 临时流默认不写
  mirror_whole_quote: false
  whole_quote_maxlen: 5000
```

| 环境变量 | 说明 |
|----------|------|
| `REDIS_URL` | 覆盖 `url` |
| `REDIS_ENABLED` | `true` / `false` |

### 9.1 健康检查（评审决议：策略 A）

Redis 为**旁路**，与 `fail_open` 一致：

- `redis.enabled=false`：不检查 Redis。
- `redis.enabled=true`：`GET /health/ready` 仍可为 **200**（proxy 可对 WS/gRPC 就绪）。
- 响应 `checks.redis`：`status: ok | degraded | unavailable`；**不因 Redis 单独失败返回 503**。

若团队将 Redis 视为硬依赖（仅 Go 消费、无 WS），可在部署文档中约定必须保证 Redis 可用，并自行用 `checks.redis.status` 做告警。

---

## 10. 依赖与部署

### 10.1 Python 依赖

```text
redis>=5.0.0,<6.0.0
```

测试开发依赖：`fakeredis>=2.0`（仅 dev/test）。

### 10.2 部署

| 场景 | 配置 |
|------|------|
| 同机 | `url: redis://127.0.0.1:6379/0`，Go 读宿主机 LAN IP |
| 跨机 | Producer 与 Redis 同机或共用 `REDIS_URL`；Redis `bind` + 防火墙放行 LAN；**一期仅改 URL，无额外代码** |

### 10.3 容量粗算

```text
50 订阅 × maxlen 2000 × ~500B ≈ 50MB 量级（加 Redis 开销）
```

---

## 11. 安全

| 风险 | 缓解 |
|------|------|
| 未授权访问 Redis | `requirepass`、bind/防火墙、不暴露公网 |
| 键可猜测 | `subscription_id` 含随机 hex |
| Go 只读 | Redis ACL：`+@read`、`~qmt:*` |

---

## 12. 可观测性

### 12.1 Producer（proxy）

| 项 | 说明 |
|----|------|
| 日志 | 连接失败、熔断、EXPIRE/DEL stream |
| 计数 | `redis_publish_total` / `redis_publish_errors`（Phase 1 可先 log 统计，Phase 2 接指标） |

### 12.2 Consumer（Go 约定）

周期性记录处理延迟，例如：

```text
lag_ms = now_ms - envelope.event.event_time_ms
# 或 now_ms - envelope.published_at_ms
```

`lag_ms` 持续升高表示消费跟不上；结合 MAXLEN 可能丢旧消息。

---

## 13. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | `fakeredis` 验证 `XADD`/`MAXLEN`/`EXPIRE`/键名 |
| 单元 | `_fanout` + mock sink |
| 集成 | `@pytest.mark.redis`，本地 Redis + 一条 mock 行情 |
| CI | `redis.enabled=false`，现有 mock 测试无回归 |

---

## 14. 实施分期

### Phase 1（MVP）— 评审锁定范围

- [ ] `redis` 配置 + `RedisStreamSink`
- [ ] `_fanout` 双写；`delete_subscription` → EXPIRE/DEL
- [ ] 仅**持久** `quote` 订阅写 Redis（`mirror_ephemeral=false`）
- [ ] REST 返回 `redis_stream_key`
- [ ] `mirror_mock`；`enabled=false` 默认
- [ ] `/health/ready` 中 `checks.redis`（策略 A，不拖垮 200）
- [ ] 单元测试（fakeredis）+ README/本文档

### Phase 2

- [ ] `mirror_whole_quote`
- [ ] `subscription_ready` 控制消息（可选）
- [ ] 熔断与指标导出
- [ ] `mirror_ephemeral` 可配置开启

### Phase 3（按需）

- [ ] 按 symbol 聚合 Stream
- [ ] 交易事件 Stream
- [ ] TLS / Sentinel

---

## 15. 风险与对策

| 风险 | 对策 |
|------|------|
| whole quote 写爆 Redis | 默认不 mirror |
| Go 落后 | 监控 `lag_ms`；调 maxlen |
| 误用 Consumer Group | 文档 + 示例仅用 XREAD |
| 一方 DELETE 影响他方 | 默认 `grace_ttl_seconds=60` |

---

## 16. 评审决议（原开放问题，已闭合）

| # | 决议 |
|---|------|
| 1 | 默认 **`grace_ttl_seconds: 60`**，不立即 DEL；急停可设 `grace_ttl_seconds: 0` + `delete_stream_on_unsubscribe: true` |
| 2 | **`redis_stream_key` 纳入 Phase 1** |
| 3 | 密码统一 **`REDIS_URL`** |
| 4 | **跨机一期支持**，仅部署改 URL / bind |
| 5 | **一期不压缩** JSON |

---

## 17. 附录 A：Go 消费者最小示例

```go
package main

import (
    "context"
    "encoding/json"
    "log"
    "time"

    "github.com/redis/go-redis/v9"
)

type Envelope struct {
    SchemaVersion  int                    `json:"schema_version"`
    SubscriptionID string                 `json:"subscription_id"`
    Event          map[string]interface{} `json:"event"`
}

func main() {
    rdb := redis.NewClient(&redis.Options{Addr: "192.168.1.10:6379"})
    streamKey := "qmt:quote:quote_xxxxxxxx" // 来自 REST redis_stream_key

    lastID := "$"
    ctx := context.Background()
    for {
        res, err := rdb.XRead(ctx, &redis.XReadArgs{
            Streams: []string{streamKey, lastID},
            Count:   100,
            Block:   5 * time.Second,
        }).Result()
        if err == redis.Nil {
            continue
        }
        if err != nil {
            log.Printf("xread: %v", err)
            time.Sleep(time.Second)
            continue
        }
        for _, msg := range res[0].Messages {
            raw := msg.Values["payload"].(string)
            var env Envelope
            if err := json.Unmarshal([]byte(raw), &env); err != nil {
                log.Printf("decode: %v", err)
                continue
            }
            _ = env.Event
            lastID = msg.ID
        }
    }
}
```

---

## 18. 附录 B：与 WebSocket 行为对照

| 项目 | WebSocket | Redis Stream |
|------|-----------|--------------|
| 连接 | 长连接 + `?token=` | `XREAD BLOCK` |
| 心跳 | `type: heartbeat` | 无（Phase 2 可选 ready 事件） |
| 载荷 | `{type, data}` | 信封 JSON → `payload` 字段 |
| 结束 | 关连接 | 停 XREAD；协调方 DELETE 订阅 |
| 广播 | 每连接一个 queue | 每读者一个 `last_id` |

---

## 19. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-06-01 | 初稿 |
| 0.2 | 2026-06-01 | 评审通过：闭合开放问题；`mirror_ephemeral`；ready 策略 A；`redis_stream_key` 进 Phase 1；`grace_ttl` 默认 60s；修正载荷表述；多标的/gRPC/跨机/消费 lag 说明 |
