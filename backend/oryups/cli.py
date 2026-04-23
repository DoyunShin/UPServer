import argparse
import os
from json import loads
from pathlib import Path

import uvicorn

BASE_DIR: Path = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the ups launcher."""
    parser = argparse.ArgumentParser(
        prog="ups",
        description="Launch UPServer via uvicorn using settings from config.json.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Path to config.json (default: <backend>/config.json)",
    )
    parser.add_argument("--host", default=None, help="Override host.ip")
    parser.add_argument("--port", type=int, default=None, help="Override host.port")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Entry point for the ``ups`` console script."""
    args = parse_args()

    config_path = Path(args.config).resolve() if args.config else BASE_DIR / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    os.environ["UPSERVER_CONFIG"] = str(config_path)

    config = loads(config_path.read_text())
    host_cfg = config["host"]
    proxy_enabled = bool(host_cfg.get("proxy", False))

    uvicorn.run(
        "oryups.main:app",
        host=args.host or host_cfg["ip"],
        port=args.port or int(host_cfg["port"]),
        proxy_headers=proxy_enabled,
        forwarded_allow_ips="*" if proxy_enabled else "127.0.0.1",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
