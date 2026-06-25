from dataclasses import dataclass


@dataclass(frozen=True)
class BridgeConfig:
    connect: str = "udpin:0.0.0.0:14551"
    http_host: str = "127.0.0.1"
    http_port: int = 8765
    source_system: int = 245
    heartbeat_timeout_s: float = 3.0

