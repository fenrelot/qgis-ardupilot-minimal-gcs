from __future__ import annotations

import argparse

from bridge.config import BridgeConfig
from bridge.http_api import make_server
from bridge.mavlink_client import MavlinkClient
from bridge.state import VehicleState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QGIS ArduBoat MAVLink bridge")
    parser.add_argument(
        "--connect",
        default=BridgeConfig.connect,
        help="pymavlink connection string",
    )
    parser.add_argument(
        "--http-host",
        default=BridgeConfig.http_host,
        help="HTTP bind host",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=BridgeConfig.http_port,
        help="HTTP bind port",
    )
    parser.add_argument(
        "--source-system",
        type=int,
        default=BridgeConfig.source_system,
        help="MAVLink source system for this bridge",
    )
    parser.add_argument(
        "--heartbeat-timeout",
        type=float,
        default=BridgeConfig.heartbeat_timeout_s,
        help="seconds before command paths refuse stale heartbeat",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = BridgeConfig(
        connect=args.connect,
        http_host=args.http_host,
        http_port=args.http_port,
        source_system=args.source_system,
        heartbeat_timeout_s=args.heartbeat_timeout,
    )
    state = VehicleState(heartbeat_timeout_s=config.heartbeat_timeout_s)
    client = MavlinkClient(config, state)
    client.start()
    server = make_server(config.http_host, config.http_port, state, client)
    print(
        f"Bridge listening on http://{config.http_host}:{config.http_port}",
        flush=True,
    )
    print(f"MAVLink connection: {config.connect}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping bridge.", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        client.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

