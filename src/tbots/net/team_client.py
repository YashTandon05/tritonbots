"""Game-controller team interface. TCP 10008, length-delimited framing.

Used for goalkeeper changes, substitution intent, and the advantage choice.
Build this LAST — we can play a full match without it.

Unlike the multicast interfaces, this is a length-delimited TCP stream, not
bare protobuf datagrams. Requests may be RSA-signed:
  - keys live in the GC's config/trusted_keys/team/<teamName>.pub.pem
  - the GC's genKey.sh generates the pair
  - the controller returns a token that must be echoed in the next request,
    which is what prevents replays
  - each team may connect only once
"""

from __future__ import annotations


class TeamClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 10008,
                 team_name: str = "TritonBots",
                 private_key: str | None = None) -> None:
        raise NotImplementedError("TASK-016")

    def connect(self) -> None:
        raise NotImplementedError("TASK-016")

    def set_goalkeeper(self, robot_id: int) -> None:
        raise NotImplementedError("TASK-016")

    def request_substitution(self) -> None:
        raise NotImplementedError("TASK-016")

    def set_advantage_choice(self, choice) -> None:
        raise NotImplementedError("TASK-016")

    def close(self) -> None:
        raise NotImplementedError("TASK-016")
