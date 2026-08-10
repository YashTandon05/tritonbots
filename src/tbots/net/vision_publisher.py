"""Turn ANY WorldState into SSL-Vision packets.

This is the single highest-value 80 lines in the repo. Once it exists,
ssl-vision-client renders BOTH backends — you watch an rSim training
rollout and a live networked match in the same browser tab, same tool.

It also means our vision serialisation is exercised constantly, so it won't
be broken the first time we actually need it.
"""

from __future__ import annotations

import time

from tbots._pb.messages_robocup_ssl_wrapper_pb2 import SSL_WrapperPacket
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import WorldState
from tbots.core.units import m_to_mm
from tbots.net.multicast import tx_socket


class VisionPublisher:
    def __init__(self, group: str = "224.5.23.2", port: int = 10006,
                 ttl: int = 0, geometry: FieldGeometry = DIV_B,
                 we_are_yellow: bool = False) -> None:
        self._sock = tx_socket(ttl=ttl)
        self._addr = (group, port)
        self._geom = geometry
        self._yellow = we_are_yellow
        self._frame = 0

    def publish(self, world: WorldState, t_capture: float | None = None) -> None:
        pkt = SSL_WrapperPacket()
        d = pkt.detection
        d.frame_number = self._frame
        self._frame += 1
        d.t_capture = t_capture if t_capture is not None else time.time()
        d.t_sent = time.time()
        d.camera_id = 0

        b = d.balls.add()
        b.confidence = 1.0
        b.x = m_to_mm(world.ball.x)
        b.y = m_to_mm(world.ball.y)
        b.z = m_to_mm(world.ball.z)
        b.pixel_x = 0.0
        b.pixel_y = 0.0

        ours = d.robots_yellow if self._yellow else d.robots_blue
        theirs = d.robots_blue if self._yellow else d.robots_yellow

        for group, robots in ((ours, world.us), (theirs, world.them)):
            for r in robots.values():
                m = group.add()
                m.confidence = 1.0
                m.robot_id = r.robot_id
                m.x = m_to_mm(r.x)          # SSL-Vision is MILLIMETERS
                m.y = m_to_mm(r.y)
                m.orientation = r.theta      # ...but RADIANS
                m.pixel_x = 0.0
                m.pixel_y = 0.0

        self._sock.sendto(pkt.SerializeToString(), self._addr)

    def publish_geometry(self) -> None:
        """Send field dimensions so the client draws the right pitch.
        Call once at startup and every few seconds thereafter."""
        pkt = SSL_WrapperPacket()
        f = pkt.geometry.field
        f.field_length = int(m_to_mm(self._geom.length))
        f.field_width = int(m_to_mm(self._geom.width))
        f.goal_width = int(m_to_mm(self._geom.goal_width))
        f.goal_depth = int(m_to_mm(self._geom.goal_depth))
        f.boundary_width = int(m_to_mm(self._geom.boundary_width))
        self._sock.sendto(pkt.SerializeToString(), self._addr)

    def close(self) -> None:
        self._sock.close()
