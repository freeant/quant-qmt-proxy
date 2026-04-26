"""统一日志工具模块。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger


_configured_sink_ids: list[int] = []
_configured_signature: tuple[Any, ...] | None = None


def _ensure_parent_dir(file_path: str | None) -> None:
    if not file_path:
        return
    log_dir = os.path.dirname(file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)


def configure_logging(
    log_level: str = "INFO",
    log_file: str | None = "logs/app.log",
    error_log_file: str | None = "logs/error.log",
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
    console_output: bool = True,
    backtrace: bool = True,
    diagnose: bool = False,
):
    """按配置签名幂等初始化 Loguru。"""

    global _configured_signature

    config_signature = (
        log_level,
        log_file,
        error_log_file,
        log_format,
        rotation,
        retention,
        compression,
        console_output,
        backtrace,
        diagnose,
    )
    if _configured_signature == config_signature and _configured_sink_ids:
        return logger

    for sink_id in list(_configured_sink_ids):
        try:
            logger.remove(sink_id)
        except ValueError:
            pass
    _configured_sink_ids.clear()

    _ensure_parent_dir(log_file)
    _ensure_parent_dir(error_log_file)

    if console_output:
        _configured_sink_ids.append(
            logger.add(
                sys.stdout,
                format=log_format,
                level=log_level,
                colorize=True,
                backtrace=backtrace,
                diagnose=diagnose,
            )
        )

    if log_file:
        _configured_sink_ids.append(
            logger.add(
                log_file,
                format=log_format,
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression=compression,
                encoding="utf-8",
                backtrace=backtrace,
                diagnose=diagnose,
            )
        )

    if error_log_file:
        _configured_sink_ids.append(
            logger.add(
                error_log_file,
                format=log_format,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression=compression,
                encoding="utf-8",
                backtrace=backtrace,
                diagnose=diagnose,
            )
        )

    _configured_signature = config_signature
    logger.info(f"日志系统已初始化 [level={log_level}, file={log_file}]")
    return logger


def configure_logging_from_settings(settings: Any):
    """根据 Settings 初始化日志。"""

    logging_settings = settings.logging
    return configure_logging(
        log_level=logging_settings.level,
        log_file=logging_settings.file or "logs/app.log",
        error_log_file=logging_settings.error_file or "logs/error.log",
        log_format=logging_settings.format,
        rotation=logging_settings.rotation,
        retention=logging_settings.retention,
        compression=logging_settings.compression,
        console_output=logging_settings.console_output,
        backtrace=logging_settings.backtrace,
        diagnose=logging_settings.diagnose,
    )


def log_runtime_configuration(surface: str, settings: Any) -> None:
    qmt_userdata_path = settings.xtquant.data.qmt_userdata_path or ""
    qmt_userdata_exists = bool(qmt_userdata_path) and Path(qmt_userdata_path).exists()
    logger.info(
        "运行时配置: "
        f"surface={surface}, "
        f"mode={settings.xtquant.mode.value}, "
        f"servers={settings.app_servers}, "
        f"app={settings.app.host}:{settings.app.port}, "
        f"grpc={settings.grpc_host}:{settings.grpc_port}, "
        f"qmt_userdata_path={qmt_userdata_path or '<unset>'}, "
        f"qmt_userdata_exists={qmt_userdata_exists}, "
        f"enable_prod_orders={settings.xtquant.trading.enable_prod_orders}, "
        f"account_profiles={len(settings.xtquant.trading.accounts)}, "
        f"api_key_enabled={bool(settings.security.api_keys)}"
    )


def get_logger(name: str | None = None):
    """返回带模块名绑定的 logger。"""

    if name:
        return logger.bind(name=name)
    return logger


def log_function_call(func_name: str, **kwargs):
    logger.debug(f"调用函数: {func_name}", extra={"params": kwargs})


def log_api_request(method: str, path: str, params: dict[str, Any] | None = None):
    logger.info(
        f"API 请求: {method} {path}",
        extra={"method": method, "path": path, "params": params},
    )


def log_api_response(path: str, status_code: int, duration_ms: float):
    level = "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR"
    logger.log(
        level,
        f"API 响应: {path} - {status_code} ({duration_ms:.2f}ms)",
        extra={"path": path, "status_code": status_code, "duration_ms": duration_ms},
    )


def log_grpc_request(service: str, method: str, request_data: dict[str, Any] | None = None):
    logger.info(
        f"gRPC 请求: {service}/{method}",
        extra={"service": service, "method": method, "request": request_data},
    )


def log_grpc_response(service: str, method: str, success: bool, duration_ms: float):
    level = "INFO" if success else "ERROR"
    result = "成功" if success else "失败"
    logger.log(
        level,
        f"gRPC 响应: {service}/{method} - {result} ({duration_ms:.2f}ms)",
        extra={"service": service, "method": method, "success": success, "duration_ms": duration_ms},
    )


def log_xtquant_call(function: str, params: dict[str, Any] | None = None):
    logger.debug(
        f"调用 xtquant: {function}",
        extra={"function": function, "params": params},
    )


def log_xtquant_result(function: str, success: bool, result: Any | None = None, error: str | None = None):
    if success:
        logger.debug(
            f"xtquant 调用成功: {function}",
            extra={"function": function, "result_type": type(result).__name__},
        )
        return
    logger.error(
        f"xtquant 调用失败: {function} - {error}",
        extra={"function": function, "error": error},
    )


def log_exception(exc: Exception, context: str | None = None):
    logger.exception(
        f"发生异常: {context or type(exc).__name__}",
        extra={"exception_type": type(exc).__name__, "context": context},
    )


def log_performance(operation: str, duration_ms: float, threshold_ms: float = 1000):
    level = "WARNING" if duration_ms > threshold_ms else "DEBUG"
    logger.log(
        level,
        f"性能: {operation} 耗时 {duration_ms:.2f}ms",
        extra={"operation": operation, "duration_ms": duration_ms},
    )


def log_data_operation(operation: str, stock_code: str | None = None, count: int | None = None):
    logger.info(
        f"数据操作: {operation}",
        extra={"operation": operation, "stock_code": stock_code, "count": count},
    )


__all__ = [
    "configure_logging",
    "configure_logging_from_settings",
    "get_logger",
    "logger",
    "log_runtime_configuration",
    "log_function_call",
    "log_api_request",
    "log_api_response",
    "log_grpc_request",
    "log_grpc_response",
    "log_xtquant_call",
    "log_xtquant_result",
    "log_exception",
    "log_performance",
    "log_data_operation",
]
