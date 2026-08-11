"""Run rSim and stream it to ssl-vision-client. The architecture proof.

    python -m tbots.apps.viz_rsim

Open http://localhost:8082 and you are watching an in-process training
simulator through the same browser tool you use for live matches.
"""

from __future__ import annotations

import argparse
import math
import time

from tbots.backends.base import Scenario
from tbots.backends.rsim import RSimBackend
from tbots.core.geometry import DIV_B
from tbots.net.vision_publisher import VisionPublisher
from tbots.skills.go_to_point import GoToPoint


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--realtime", action="store_true",
                   help="sleep to match wall clock (needed to actually watch)")
    p.add_argument("--seconds", type=float, default=60.0)
    p.add_argument("--port", type=int, default=10006,
                   help="vision multicast port. Default 10006 matches "
                        "VisionPublisher and a native ssl-vision-client "
                        "(macOS, or Step 13's local workaround). The "
                        "docker-compose vision-client listens on 10020 "
                        "instead (it shares the port with the ER-Force "
                        "simulator container) -- pass --port 10020 when "
                        "watching through `docker compose up -d`.")
    args = p.parse_args()

    backend = RSimBackend(n_us=6, n_them=6, dt=1.0 / 60.0, geometry=DIV_B)
    pub = VisionPublisher(geometry=DIV_B, port=args.port)
    pub.publish_geometry()

    world = backend.reset(Scenario.kickoff())
    skills = {i: GoToPoint(target=(0.0, 0.0)) for i in range(6)}
    for i, s in skills.items():
        s.reset(world, i)

    n_ticks = int(args.seconds / backend.dt)
    t0 = time.time()
    for tick in range(n_ticks):
        # Make the robots orbit, so there is obviously something happening.
        phase = tick * backend.dt * 0.5
        for i, s in skills.items():
            a = phase + i * (2 * math.pi / 6)
            s.target = (2.0 * math.cos(a), 1.5 * math.sin(a))

        cmds = [skills[i].step(world, i) for i in range(6)]
        world = backend.step(cmds)
        pub.publish(world)

        if tick % 300 == 0:
            pub.publish_geometry()
        if args.realtime:
            target = t0 + (tick + 1) * backend.dt
            time.sleep(max(0.0, target - time.time()))

    elapsed = time.time() - t0
    print(f"{n_ticks} ticks in {elapsed:.2f}s "
          f"= {n_ticks / elapsed:,.0f} steps/s "
          f"({n_ticks * backend.dt / elapsed:.1f}x realtime)")
    pub.close()
    backend.close()


if __name__ == "__main__":
    main()
