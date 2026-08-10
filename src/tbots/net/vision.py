"""Receive SSL-Vision detection frames and merge them into world frames.

Joins 224.5.23.2:10006, parses SSL_WrapperPacket, buffers detection frames
per camera_id, and merges them into one world frame by t_capture.

Division B uses four cameras at roughly 60 Hz each, so you will receive
~240 packets/second, staggered. DO NOT run the control loop once per
packet — merge, then tick once.
"""

from __future__ import annotations


class VisionReceiver:
    def __init__(self, group: str = "224.5.23.2", port: int = 10006) -> None:
        raise NotImplementedError("TASK-010")

    def wait_for_next_frame(self, timeout: float = 0.05) -> bool:
        raise NotImplementedError("TASK-010")

    def frames(self) -> list:
        """The merged detection frames since the last call."""
        raise NotImplementedError("TASK-010")

    def close(self) -> None:
        raise NotImplementedError("TASK-010")
