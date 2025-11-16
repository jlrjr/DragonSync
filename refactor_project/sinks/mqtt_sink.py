"""MQTT Sink - CoT XML to JSON for Home Assistant/MQTT.

The MQTT Sink parses CoT XML and converts it to JSON format for MQTT publish.
This is primarily designed for Home Assistant integration via MQTT device trackers.
"""

import json
import xml.etree.ElementTree as ET
from typing import Protocol, Optional
from refactor_project.sinks.base_sink import BaseSink


class MqttClient(Protocol):
    """Protocol for MQTT client interface.

    This allows dependency injection with any object that has publish/close methods.
    """

    def publish(self, topic: str, payload: str) -> None:
        """Publish payload to MQTT topic."""
        ...

    def close(self) -> None:
        """Close the MQTT connection."""
        ...


class MqttSink(BaseSink):
    """MQTT Sink - converts CoT XML to JSON and publishes to MQTT.

    This sink parses CoT XML to extract position and telemetry data,
    converts it to JSON format, and publishes to MQTT topics for
    Home Assistant device tracking.

    Topic format: {topic_prefix}/{uid}
    Payload: JSON with latitude, longitude, altitude, etc.
    """

    def __init__(self, client: MqttClient, topic_prefix: str = "dragonsync"):
        """Initialize MQTT Sink.

        Args:
            client: MQTT client for publishing messages.
            topic_prefix: MQTT topic prefix (default: "dragonsync").
        """
        self.client = client
        self.topic_prefix = topic_prefix

    def publish_cot_event(self, cot_xml: bytes) -> None:
        """Parse CoT XML and publish as JSON to MQTT.

        Args:
            cot_xml: CoT XML event as bytes.

        Raises:
            xml.etree.ElementTree.ParseError: If CoT XML is malformed.
            Exception: If unable to publish to MQTT.
        """
        # Parse CoT XML
        root = ET.fromstring(cot_xml)

        # Extract basic event attributes
        uid = root.get('uid')
        event_type = root.get('type')
        time = root.get('time')

        # Extract point data
        point = root.find('point')
        if point is None:
            raise ValueError(f"CoT event {uid} missing <point> element")

        lat = float(point.get('lat', 0.0))
        lon = float(point.get('lon', 0.0))
        hae = float(point.get('hae', 0.0))
        ce = float(point.get('ce', 0.0))
        le = float(point.get('le', 0.0))

        # Build base JSON payload
        data = {
            'uid': uid,
            'type': event_type,
            'latitude': lat,
            'longitude': lon,
            'altitude': hae,
            'horizontal_accuracy': ce,
            'vertical_accuracy': le,
            'timestamp': time
        }

        # Extract optional track data
        detail = root.find('detail')
        if detail is not None:
            track = detail.find('track')
            if track is not None:
                course = track.get('course')
                speed = track.get('speed')
                if course is not None:
                    data['course'] = float(course)
                if speed is not None:
                    data['speed'] = float(speed)

            # Extract callsign from contact element
            contact = detail.find('contact')
            if contact is not None:
                callsign = contact.get('callsign')
                if callsign:
                    data['callsign'] = callsign

            # Extract remarks
            remarks = detail.find('remarks')
            if remarks is not None and remarks.text:
                data['remarks'] = remarks.text

        # Clean up None values
        data = {k: v for k, v in data.items() if v is not None}

        # Publish to MQTT
        topic = f"{self.topic_prefix}/{uid}"
        payload = json.dumps(data)
        self.client.publish(topic, payload)

    def mark_inactive(self, uid: str) -> None:
        """Publish empty payload to clear device from Home Assistant.

        Args:
            uid: Unique identifier of the entity to mark as inactive.

        Note:
            Publishing an empty string to the device's topic will cause
            Home Assistant to remove it from the map.
        """
        topic = f"{self.topic_prefix}/{uid}"
        self.client.publish(topic, "")

    def close(self) -> None:
        """Close the MQTT client connection.

        Note:
            Calls client.close() if available. Gracefully handles clients
            without a close method.
        """
        if hasattr(self.client, 'close'):
            self.client.close()
