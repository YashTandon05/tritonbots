"""Turn ANY WorldState into SSL-Vision packets.

This is the single highest-value 80 lines in the repo. Once it exists,
ssl-vision-client renders BOTH backends — you watch an rSim training
rollout and a live networked match in the same browser tab, same tool.

It also means our vision serialisation is exercised constantly, so it won't
be broken the first time we actually need it.
"""

from __future__ import annotations

import math
import time

from tbots._pb.messages_robocup_ssl_geometry_pb2 import SSL_FieldShapeType
from tbots._pb.messages_robocup_ssl_wrapper_pb2 import SSL_WrapperPacket
from tbots.core.geometry import DIV_B, FieldGeometry
from tbots.core.state import WorldState
from tbots.core.units import m_to_mm
from tbots.net.multicast import tx_socket

# SSL line markings are 10 mm wide. Not in FieldGeometry: it is a drawing
# property, not a dimension anything above the backend reasons about.
_LINE_THICKNESS_MM = 10


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
        f.penalty_area_depth = int(m_to_mm(self._geom.penalty_depth))
        f.penalty_area_width = int(m_to_mm(self._geom.penalty_width))
        f.center_circle_radius = int(m_to_mm(self._geom.center_circle_radius))
        f.line_thickness = _LINE_THICKNESS_MM

        # The client draws NOTHING but a default centre circle unless these
        # are populated -- field_length/width alone size the canvas, they do
        # not produce markings. Names and shape types are the league's, not
        # ours; ssl-vision-client matches on them.
        hl = m_to_mm(self._geom.half_length)
        hw = m_to_mm(self._geom.half_width)
        pd = m_to_mm(self._geom.penalty_depth)
        phw = m_to_mm(self._geom.penalty_width) / 2.0

        for name, p1, p2 in (
            ("TopTouchLine", (-hl, hw), (hl, hw)),
            ("BottomTouchLine", (-hl, -hw), (hl, -hw)),
            ("LeftGoalLine", (-hl, -hw), (-hl, hw)),
            ("RightGoalLine", (hl, -hw), (hl, hw)),
            ("HalfwayLine", (0.0, -hw), (0.0, hw)),
            ("CenterLine", (-hl, 0.0), (hl, 0.0)),
            ("LeftPenaltyStretch", (-hl + pd, -phw), (-hl + pd, phw)),
            ("RightPenaltyStretch", (hl - pd, -phw), (hl - pd, phw)),
            ("LeftFieldLeftPenaltyStretch", (-hl, phw), (-hl + pd, phw)),
            ("LeftFieldRightPenaltyStretch", (-hl, -phw), (-hl + pd, -phw)),
            ("RightFieldLeftPenaltyStretch", (hl, phw), (hl - pd, phw)),
            ("RightFieldRightPenaltyStretch", (hl, -phw), (hl - pd, -phw)),
        ):
            ln = f.field_lines.add()
            ln.name = name
            ln.p1.x, ln.p1.y = p1
            ln.p2.x, ln.p2.y = p2
            ln.thickness = float(_LINE_THICKNESS_MM)
            ln.type = SSL_FieldShapeType.Value(name)

        arc = f.field_arcs.add()
        arc.name = "CenterCircle"
        arc.center.x = 0.0
        arc.center.y = 0.0
        arc.radius = m_to_mm(self._geom.center_circle_radius)
        arc.a1 = 0.0
        arc.a2 = 2.0 * math.pi
        arc.thickness = float(_LINE_THICKNESS_MM)
        arc.type = SSL_FieldShapeType.Value("CenterCircle")

        self._sock.sendto(pkt.SerializeToString(), self._addr)

    def close(self) -> None:
        self._sock.close()
