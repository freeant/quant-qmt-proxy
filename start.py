from __future__ import annotations

import argparse
import os

from app.config import get_settings, reset_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xtquant-proxy bootstrap")
    parser.add_argument("--mode", choices=["mock", "dev", "prod"], default="mock")
    parser.add_argument("--servers", choices=["all", "grpc", "rest"], default="all")
    parser.add_argument("--host", default=None, help="REST host override")
    parser.add_argument("--port", type=int, default=None, help="REST port override")
    parser.add_argument("--grpc-host", default=None, help="gRPC host override")
    parser.add_argument("--grpc-port", type=int, default=None, help="gRPC port override")
    parser.add_argument("--reload", action="store_true", help="Enable FastAPI reload in rest-only mode")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    os.environ["APP_MODE"] = args.mode
    os.environ["APP_SERVERS"] = args.servers
    if args.reload:
        os.environ["APP_DEBUG"] = "true"
    else:
        os.environ.pop("APP_DEBUG", None)
    if args.host:
        os.environ["APP_HOST"] = args.host
    if args.port is not None:
        os.environ["APP_PORT"] = str(args.port)
    if args.grpc_host:
        os.environ["GRPC_HOST"] = args.grpc_host
    if args.grpc_port is not None:
        os.environ["GRPC_PORT"] = str(args.grpc_port)

    reset_settings()
    settings = get_settings()

    print("=" * 60)
    print(f"{settings.app.name} {settings.app.version}")
    print("=" * 60)
    print(f"mode      : {settings.xtquant.mode.value}")
    print(f"servers   : {settings.app_servers}")
    print(f"rest      : http://{settings.app.host}:{settings.app.port}")
    print(f"grpc      : {settings.grpc_host}:{settings.grpc_port}")
    print(f"debug     : {settings.app.debug}")
    print("=" * 60)

    from run import main as run_main

    run_main()


if __name__ == "__main__":
    main()
