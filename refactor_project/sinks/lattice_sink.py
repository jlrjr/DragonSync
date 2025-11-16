"""Lattice Sink - CoT XML to Lattice entity format.

The Lattice Sink parses CoT XML and converts it to Lattice/Anduril API format
for entity tracking and Common Operating Picture (COP) integration.
"""

import xml.etree.ElementTree as ET
from typing import Protocol
from refactor_project.sinks.base_sink import BaseSink


class LatticeClient(Protocol):
    """Protocol for Lattice client interface.

    This allows dependency injection with any object implementing Lattice API calls.
    """

    def publish_entity(self, **entity_data) -> None:
        """Publish entity to Lattice."""
        ...

    def expire_entity(self, entity_id: str) -> None:
        """Expire/remove entity from Lattice."""
        ...

    def close(self) -> None:
        """Close the Lattice connection."""
        ...


class LatticeSink(BaseSink):
    """Lattice Sink - converts CoT XML to Lattice entity format.

    This sink parses CoT XML to extract position and entity data,
    converts it to Lattice/Anduril API format, and publishes to
    the Lattice platform for Common Operating Picture integration.

    Entity format follows Lattice Entity API requirements.
    """

    def __init__(self, client: LatticeClient):
        """Initialize Lattice Sink.

        Args:
            client: Lattice client for entity publishing.
        """
        self.client = client

    def publish_cot_event(self, cot_xml: bytes) -> None:
        """Parse CoT XML and publish as Lattice entity.

        Args:
            cot_xml: CoT XML event as bytes.

        Raises:
            xml.etree.ElementTree.ParseError: If CoT XML is malformed.
            Exception: If unable to publish to Lattice API.
        """
        # Parse CoT XML
        root = ET.fromstring(cot_xml)

        # Extract basic event attributes
        uid = root.get('uid')
        cot_type = root.get('type', '')
        time = root.get('time')

        # Extract point data
        point = root.find('point')
        if point is None:
            raise ValueError(f"CoT event {uid} missing <point> element")

        lat = float(point.get('lat', 0.0))
        lon = float(point.get('lon', 0.0))
        hae = float(point.get('hae', 0.0))

        # Determine entity type from CoT type code
        entity_type = self._determine_entity_type(cot_type)

        # Build Lattice entity data
        entity_data = {
            'entity_id': uid,
            'latitude': lat,
            'longitude': lon,
            'altitude': hae,
            'entity_type': entity_type,
            'timestamp': time,
            'cot_type': cot_type
        }

        # Extract optional metadata from detail element
        detail = root.find('detail')
        if detail is not None:
            # Extract callsign from contact element
            contact = detail.find('contact')
            if contact is not None:
                callsign = contact.get('callsign')
                if callsign:
                    entity_data['callsign'] = callsign

            # Extract track data
            track = detail.find('track')
            if track is not None:
                course = track.get('course')
                speed = track.get('speed')
                if course is not None:
                    entity_data['course'] = float(course)
                if speed is not None:
                    entity_data['speed'] = float(speed)

            # Extract remarks
            remarks = detail.find('remarks')
            if remarks is not None and remarks.text:
                entity_data['remarks'] = remarks.text

        # Publish to Lattice
        self.client.publish_entity(**entity_data)

    def _determine_entity_type(self, cot_type: str) -> str:
        """Determine entity type from CoT type code.

        Args:
            cot_type: CoT type code (e.g., a-u-A-M-H-Q for rotary drone).

        Returns:
            Entity type string for Lattice ('drone', 'aircraft', 'vessel', etc.)
        """
        # Parse CoT type hierarchy
        # Format: affiliation-dimension-function-...
        # Example: a-u-A-M-H-Q = friendly-unmanned-air-military-rotary-drone

        parts = cot_type.split('-')
        if len(parts) < 3:
            return 'unknown'

        dimension = parts[1] if len(parts) > 1 else ''

        # Check for unmanned (drones)
        if 'u' in dimension.lower():
            return 'drone'

        # Check for air
        if dimension.upper() == 'A':
            return 'aircraft'

        # Check for surface (ships)
        if dimension.upper() == 'S':
            return 'vessel'

        # Check for ground
        if dimension.upper() == 'G':
            return 'ground_vehicle'

        return 'unmanned' if 'u' in dimension.lower() else 'unknown'

    def mark_inactive(self, uid: str) -> None:
        """Expire entity in Lattice (mark as inactive).

        Args:
            uid: Unique identifier of the entity to expire.

        Note:
            Lattice uses entity expiration to remove stale entities
            from the Common Operating Picture.
        """
        self.client.expire_entity(entity_id=uid)

    def close(self) -> None:
        """Close the Lattice client connection.

        Note:
            Calls client.close() if available. Gracefully handles clients
            without a close method.
        """
        if hasattr(self.client, 'close'):
            self.client.close()
