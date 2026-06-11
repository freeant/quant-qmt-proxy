"""Shared thread pool for blocking xtquant / IO work."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, TypeVar

_T = TypeVar("_T")

_EXECUTOR: ThreadPoolExecutor | None = None
_DEFAULT_MAX_WORKERS = 40


def get_blocking_executor(max_workers: int = _DEFAULT_MAX_WORKERS) -> ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="blocking")
    return _EXECUTOR


def run_blocking(
    func: Callable[..., _T],
    /,
    *args,
    timeout: float | None = None,
    **kwargs,
) -> _T:
    future = get_blocking_executor().submit(func, *args, **kwargs)
    return future.result(timeout=timeout)


async def run_blocking_async(func: Callable[..., _T], /, *args, **kwargs) -> _T:
    loop = asyncio.get_running_loop()
    bound = partial(func, *args, **kwargs)
    return await loop.run_in_executor(get_blocking_executor(), bound)
