"""Tests for MQTT Sink (CoT → JSON)."""

import pytest
import json
from unittest.mock import Mock, call
from refactor_project.sinks.mqtt_sink import MqttSink
from refactor_project.sinks.base_sink import BaseSink


# Sample CoT XML for testing
SAMPLE_DRONE_COT = b'''<event version="2.0" uid="drone-123" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z" how="m-g">
<point lat="37.7749" lon="-122.4194" hae="100.0" ce="35.0" le="25.0"/>
<detail>
  <track course="180.0" speed="15.5"/>
  <remarks>Test Drone</remarks>
  <contact callsign="DRONE-ABC"/>
</detail>
</event>'''

MINIMAL_COT = b'''<event version="2.0" uid="drone-minimal" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z" how="m-g">
<point lat="37.0" lon="-122.0" hae="50.0" ce="10.0" le="5.0"/>
</event>'''


class TestMqttSinkInterface:
    """Test MQTT Sink implements BaseSink correctly."""

    def test_mqtt_sink_is_base_sink(self):
        """MqttSink should inherit from BaseSink."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="test")
        assert isinstance(sink, BaseSink)

    def test_mqtt_sink_requires_client_and_topic(self):
        """MqttSink should require client and topic prefix."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="dragonsync")
        assert sink.client is mock_client
        assert sink.topic_prefix == "dragonsync"

    def test_mqtt_sink_default_topic_prefix(self):
        """MqttSink should have default topic prefix."""
        mock_client = Mock()
        sink = MqttSink(mock_client)
        assert sink.topic_prefix == "dragonsync"


class TestMqttSinkCotParsing:
    """Test CoT XML parsing."""

    def test_parses_drone_cot_to_dict(self):
        """Should parse CoT XML and extract position data."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        # Should have published to MQTT
        assert mock_client.publish.called

        # Extract published JSON
        topic, payload = mock_client.publish.call_args[0]
        data = json.loads(payload)

        # Verify extracted data
        assert data['uid'] == 'drone-123'
        assert data['latitude'] == 37.7749
        assert data['longitude'] == -122.4194
        assert data['altitude'] == 100.0
        assert data['type'] == 'a-u-A-M-H-Q'

    def test_extracts_track_data(self):
        """Should extract track data (course, speed) from CoT."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        topic, payload = mock_client.publish.call_args[0]
        data = json.loads(payload)

        assert 'course' in data
        assert data['course'] == 180.0
        assert 'speed' in data
        assert data['speed'] == 15.5

    def test_extracts_accuracy_values(self):
        """Should extract CE/LE accuracy values."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        topic, payload = mock_client.publish.call_args[0]
        data = json.loads(payload)

        assert 'horizontal_accuracy' in data
        assert data['horizontal_accuracy'] == 35.0
        assert 'vertical_accuracy' in data
        assert data['vertical_accuracy'] == 25.0

    def test_extracts_callsign(self):
        """Should extract callsign from contact element."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        topic, payload = mock_client.publish.call_args[0]
        data = json.loads(payload)

        assert 'callsign' in data
        assert data['callsign'] == 'DRONE-ABC'

    def test_handles_minimal_cot(self):
        """Should handle CoT with minimal elements."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(MINIMAL_COT)

        topic, payload = mock_client.publish.call_args[0]
        data = json.loads(payload)

        # Should have required fields
        assert data['uid'] == 'drone-minimal'
        assert data['latitude'] == 37.0
        assert data['longitude'] == -122.0
        assert data['altitude'] == 50.0

        # Optional fields should have defaults or be absent
        assert data.get('course') is None
        assert data.get('speed') is None
        assert data.get('callsign') is None


class TestMqttSinkPublish:
    """Test MQTT publishing."""

    def test_publishes_to_correct_topic(self):
        """Should publish to topic with UID."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="test")

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        topic, payload = mock_client.publish.call_args[0]
        assert topic == "test/drone-123"

    def test_publishes_valid_json(self):
        """Published payload should be valid JSON."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        topic, payload = mock_client.publish.call_args[0]

        # Should not raise JSONDecodeError
        data = json.loads(payload)
        assert isinstance(data, dict)

    def test_publishes_multiple_events(self):
        """Can publish multiple different drones."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="multi")

        cot1 = b'<event uid="drone-1" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z"><point lat="1.0" lon="2.0" hae="3.0" ce="4.0" le="5.0"/></event>'
        cot2 = b'<event uid="drone-2" type="a-u-A-M-F-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z"><point lat="10.0" lon="20.0" hae="30.0" ce="40.0" le="50.0"/></event>'

        sink.publish_cot_event(cot1)
        sink.publish_cot_event(cot2)

        assert mock_client.publish.call_count == 2

        # Check topics
        call1_topic = mock_client.publish.call_args_list[0][0][0]
        call2_topic = mock_client.publish.call_args_list[1][0][0]
        assert call1_topic == "multi/drone-1"
        assert call2_topic == "multi/drone-2"

    def test_handles_invalid_xml(self):
        """Should handle invalid XML gracefully."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        invalid_cot = b'<invalid xml'

        # Should raise an error or log warning
        with pytest.raises(Exception):  # XML parsing error
            sink.publish_cot_event(invalid_cot)


class TestMqttSinkMarkInactive:
    """Test mark_inactive method."""

    def test_mark_inactive_publishes_empty_payload(self):
        """mark_inactive should publish empty payload to clear device."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="test")

        sink.mark_inactive("drone-xyz")

        mock_client.publish.assert_called_once_with("test/drone-xyz", "")

    def test_mark_inactive_multiple_drones(self):
        """Can mark multiple drones as inactive."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="cleanup")

        sink.mark_inactive("drone-1")
        sink.mark_inactive("drone-2")
        sink.mark_inactive("drone-3")

        assert mock_client.publish.call_count == 3
        mock_client.publish.assert_has_calls([
            call("cleanup/drone-1", ""),
            call("cleanup/drone-2", ""),
            call("cleanup/drone-3", "")
        ])


class TestMqttSinkClose:
    """Test close method."""

    def test_close_calls_client_close(self):
        """close should call client.close()."""
        mock_client = Mock()
        sink = MqttSink(mock_client)

        sink.close()

        mock_client.close.assert_called_once()

    def test_close_handles_missing_client_close(self):
        """close should handle client without close method."""
        mock_client = Mock(spec=[])  # No close method
        sink = MqttSink(mock_client)

        # Should not raise error
        sink.close()


class TestMqttSinkIntegration:
    """Integration-style tests."""

    def test_full_lifecycle(self):
        """Test full lifecycle: publish events, mark inactive, close."""
        mock_client = Mock()
        sink = MqttSink(mock_client, topic_prefix="lifecycle")

        # Publish some events
        sink.publish_cot_event(SAMPLE_DRONE_COT)
        sink.publish_cot_event(MINIMAL_COT)

        # Mark one as inactive
        sink.mark_inactive("drone-123")

        # Close
        sink.close()

        # Verify all calls
        assert mock_client.publish.call_count == 3  # 2 events + 1 inactive
        mock_client.close.assert_called_once()
