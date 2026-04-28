"""AxlClient, a stdlib HTTP wrapper for the local AXL node API.

Ports the request shape used by Gensyn's autoresearch demo
(research_network.py) so HackSim agents talk to AXL the same way the
upstream demo does. Pure urllib, no third-party HTTP dependency.
"""

from .client import (
    AxlClient,
    AxlError,
    ReceivedMessage,
    Topology,
    PeerInfo,
)

__all__ = [
    "AxlClient",
    "AxlError",
    "ReceivedMessage",
    "Topology",
    "PeerInfo",
]
