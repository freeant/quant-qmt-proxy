# 生产运维：自动重启与僵死恢复

本文说明如何在 Windows 上让 `quant-qmt-proxy` 在**崩溃**或**僵死**后自动恢复。

## 架构

| 层级 | 组件 | 作用 |
| --- | --- | --- |
| L1 | NSSM Windows 服务 | 进程退出后自动拉起 |
| L1 | `scripts/watchdog.ps1` | 探测 `/health/live`，僵死时重启 |
| L2 | `/health/live` 心跳字段 | 区分「进程在」与「事件循环真活」 |

**不要用** `/health/ready` 触发重启：QMT 未登录时 `ready` 会 503，但 proxy 本身可能正常，反复重启无意义。

## 前置条件

- Windows，项目已安装依赖（`.venv`）
- `dev/prod` 模式需本机 MiniQMT 已登录
- NSSM：可手动安装并加入 `PATH`，或由安装脚本自动下载到 `tools/nssm/`（见下文）
- `.env` / `config.local.yml` 已配置

## 1. 安装 Windows 服务（NSSM）

在**管理员 PowerShell**（右键「以管理员身份运行」）中，于项目根目录执行：

```powershell
# 首次安装：若无 NSSM，脚本会自动下载到 tools\nssm\
.\scripts\install-service.ps1 -Action Install

# 或显式指定下载
.\scripts\install-service.ps1 -Action Install -BootstrapNssm
```

说明：

- 若本机未安装 NSSM，`-Action Install` 会自动从 GitHub 镜像下载到 `tools\nssm\nssm.exe`（官方站 `nssm.cc` 不可用时也会尝试备用源）。
- **必须用管理员权限**，否则会报 `Administrator access is needed`。

若已手动安装 NSSM，也可：

```powershell
.\scripts\install-service.ps1 -Action Install -NssmPath "C:\nssm\win64\nssm.exe"
```

常用命令：

```powershell
.\scripts\install-service.ps1 -Action Status
.\scripts\install-service.ps1 -Action Restart
.\scripts\install-service.ps1 -Action Uninstall
```

服务默认名：`xtquant-proxy`。安装脚本会：

- 使用 `.venv\Scripts\python.exe run.py`
- 工作目录设为项目根
- 从 `.env` 注入环境变量（`AppEnvironmentExtra`）
- 标准输出/错误写入 `logs/service.out.log`、`logs/service.err.log`
- 退出后 5 秒自动重启（`AppExit Default Restart`）

## 2. 启动 Watchdog（僵死恢复）

另开一个终端或注册为计划任务，长期运行：

```powershell
.\scripts\watchdog.ps1
```

默认每 30 秒请求 `/health/live`（超时 5 秒）。K 线自动下载可能耗时较长，但已在后台线程执行，**不应**再阻塞健康检查。若仍频繁超时，可调大 `-RequestTimeoutSeconds`。

```text
GET http://127.0.0.1:8000/health/live
```

连续 **3 次**失败，或 `heartbeat_age_seconds` **> 60**，则重启服务（优先 NSSM `restart`，否则杀 `run.py` 进程后拉起）。

可调参数示例：

```powershell
.\scripts\watchdog.ps1 `
  -HealthUrl "http://127.0.0.1:8000/health/live" `
  -IntervalSeconds 30 `
  -FailureThreshold 3 `
  -RequestTimeoutSeconds 5 `
  -HeartbeatMaxAgeSeconds 60 `
  -ServiceName "xtquant-proxy"
```

日志：`logs/watchdog.log`

### 将 Watchdog 注册为计划任务（可选）

1. 任务计划程序 → 创建任务 → 触发器「登录时」或「启动时」
2. 操作：启动程序 `powershell.exe`
3. 参数：`-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\quant-qmt-proxy\scripts\watchdog.ps1"`
4. 勾选「不管用户是否登录都要运行」（需管理员）

## 3. `/health/live` 响应字段

| 字段 | 说明 |
| --- | --- |
| `pid` | 当前进程 ID |
| `started_at_ms` | 进程启动时间（毫秒时间戳） |
| `last_heartbeat_ms` | 最近一次心跳时间 |
| `uptime_seconds` | 运行时长 |
| `heartbeat_age_seconds` | 距上次心跳的秒数；僵死时持续增大 |

后台线程每 10 秒更新心跳；每次请求 `/health/live` 也会刷新。

## 4. 故障场景对照

| 现象 | 建议 |
| --- | --- |
| 进程崩溃、端口消失 | NSSM 自动重启 |
| 接口超时、`live` 无响应 | Watchdog 重启 |
| `heartbeat_age_seconds` 持续 > 60 | Watchdog 重启 |
| `ready` 503、QMT 未连 | 检查 MiniQMT 登录，**不要**靠重启 proxy 解决 |
| 仅 `APP_SERVERS=grpc` | 无 REST `/health/live`，Watchdog 需改探测 gRPC 端口或另启 REST |

## 5. 推荐 prod 只读配置

```env
APP_MODE=prod
APP_SERVERS=all
APP_ENABLE_PROD_ORDERS=false
```

MiniQMT 与 proxy 建议部署在**同一台机器**，`QMT_USERDATA_PATH` 指向 `userdata_mini`。

## 6. 手动验证

```powershell
curl http://127.0.0.1:8000/health/live
Get-Service xtquant-proxy
Get-Content logs\watchdog.log -Tail 20
Get-Content logs\service.err.log -Tail 50
```
