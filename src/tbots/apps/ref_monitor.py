"""Print the game state whenever it changes. Proves the referee link works.

    python -m tbots.apps.ref_monitor --team "TritonBots"

Then click buttons in the game controller UI and watch lines appear.
"""

from __future__ import annotations

import argparse
import time

from tbots.net.referee import RefereeReceiver


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--team", default="TritonBots")
    p.add_argument("--group", default="224.5.23.1")
    p.add_argument("--port", type=int, default=10003)
    args = p.parse_args()

    rx = RefereeReceiver(group=args.group, port=args.port, team_name=args.team)
    print(f"listening on {args.group}:{args.port} as '{args.team}' ...")
    print("(if nothing appears, the GC is not running or is on other ports)")

    last_counter = -1
    try:
        while True:
            gs = rx.poll()
            if gs.counter != last_counter:
                last_counter = gs.counter
                print(
                    f"[{gs.counter:5d}] {gs.play.name:<16} "
                    f"ours={gs.ours!s:<5} "
                    f"move={gs.can_move!s:<5} touch={gs.can_touch_ball!s:<5} "
                    f"score={gs.our_score}-{gs.their_score} "
                    f"gk={gs.our_goalkeeper} max_bots={gs.our_max_robots} "
                    f"yellow_team={rx.we_are_yellow} flip_x={rx.flip_x}"
                )
            time.sleep(0.02)
    except KeyboardInterrupt:
        rx.close()


if __name__ == "__main__":
    main()
