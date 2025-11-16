"""TAK Sink - CoT passthrough to TAK servers.

The TAK Sink is the simplest sink - it receives CoT XML (the universal format)
and passes it through unchanged to TAK endpoints (multicast or TCP/TLS).
"""

from typing import Protocol
from datetime import datetime, timezone, timedelta
from refactor_project.sinks.base_sink import BaseSink


class TakClient(Protocol):
    """Protocol for TAK client interface.

    This allows dependency injection with any object that has a send method.
    """

    def send(self, cot_xml: bytes) -> None:
        """Send CoT XML to TAK endpoint."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


class TakSink(BaseSink):
    """TAK Sink - passes CoT XML through to TAK servers.

    This sink is a simple passthrough - it receives CoT XML (already in TAK's
    native format) and sends it directly to the TAK endpoint without parsing
    or modification.

    The client handles the actual I/O (multicast UDP, TCP, TLS, etc.).
    """

    def __init__(self, client: TakClient):
        """Initialize TAK Sink.

        Args:
            client: TAK client for sending CoT messages (multicast, TCP, etc.)
        """
        self.client = client

    def publish_cot_event(self, cot_xml: bytes) -> None:
        """Publish CoT event to TAK server/multicast.

        Args:
            cot_xml: CoT XML event as bytes.

        Raises:
            ConnectionError: If unable to send to TAK endpoint.

        Note:
            This is a passthrough - CoT XML is sent unchanged to TAK.
        """
        self.client.send(cot_xml)

    def mark_inactive(self, uid: str) -> None:
        """Send CoT deletion event for inactive entity.

        Args:
            uid: Unique identifier of the entity to mark as inactive.

        Note:
            TAK uses special deletion events (type t-x-d-d) to remove entities
            from the map. This generates and sends a deletion CoT event.
        """
        # Generate CoT deletion event
        now = datetime.now(timezone.utc)
        stale = now + timedelta(seconds=10)

        time_str = now.isoformat().replace('+00:00', 'Z')
        stale_str = stale.isoformat().replace('+00:00', 'Z')

        # TAK deletion event format
        deletion_cot = f'''<event version="2.0" uid="{uid}" type="t-x-d-d" time="{time_str}" start="{time_str}" stale="{stale_str}" how="h-e">
<point lat="0.0" lon="0.0" hae="0.0" ce="9999999.0" le="9999999.0"/>
<detail>
  <link uid="{uid}" relation="p-p" type="a-f-G-E-V-C"/>
</detail>
</event>'''

        self.client.send(deletion_cot.encode('utf-8'))

    def close(self) -> None:
        """Close the TAK client connection.

        Note:
            Calls client.close() if available. Gracefully handles clients
            without a close method.
        """
        if hasattr(self.client, 'close'):
            self.client.close()
