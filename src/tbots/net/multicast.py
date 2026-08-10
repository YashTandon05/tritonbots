"""UDP multicast helpers.

Two things every new person needs to know:

1. League multicast packets are BARE PROTOBUF. One message per datagram,
   no length prefix. Just ParseFromString(data).
   The TCP interfaces (game-controller team client on 10008, CI on 10009)
   are length-delimited streams instead — different framing entirely.

2. In development, ALWAYS set multicast TTL to 0. TTL 0 means the packet
   never leaves this host. Without it, two people on the same lab wifi will
   silently referee each other's matches, and you will lose an afternoon.
"""

from __future__ import annotations

import socket
import struct


def rx_socket(group: str, port: int, iface: str = "0.0.0.0",
              blocking: bool = False) -> socket.socket:
    """Join a multicast group and return a socket ready to recvfrom()."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    s.bind(("", port))
    mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton(iface))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.setblocking(blocking)
    return s


def tx_socket(ttl: int = 0, iface: str = "0.0.0.0") -> socket.socket:
    """Socket for sending multicast. ttl=0 keeps packets on this host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                 socket.inet_aton(iface))
    return s


def drain(sock: socket.socket, bufsize: int = 65535) -> list[bytes]:
    """Read every pending datagram without blocking. Newest is last.

    Call this once per control tick. Never block the control loop on a
    socket: one dropped packet would stall all six robots.
    """
    out: list[bytes] = []
    while True:
        try:
            out.append(sock.recv(bufsize))
        except (BlockingIOError, InterruptedError):
            return out
        except OSError:
            return out
