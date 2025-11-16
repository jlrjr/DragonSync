"""Tests for Lattice Sink (CoT → Lattice API format)."""

import pytest
from unittest.mock import Mock, call
from refactor_project.sinks.lattice_sink import LatticeSink
from refactor_project.sinks.base_sink import BaseSink


# Sample CoT XML for testing
SAMPLE_DRONE_COT = b'''<event version="2.0" uid="drone-123" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z" how="m-g">
<point lat="37.7749" lon="-122.4194" hae="100.0" ce="35.0" le="25.0"/>
<detail>
  <track course="180.0" speed="15.5"/>
  <contact callsign="DRONE-ABC"/>
</detail>
</event>'''

MINIMAL_COT = b'''<event version="2.0" uid="drone-minimal" type="a-u-A-M-F-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z" how="m-g">
<point lat="37.0" lon="-122.0" hae="50.0" ce="10.0" le="5.0"/>
</event>'''


class TestLatticeSinkInterface:
    """Test Lattice Sink implements BaseSink correctly."""

    def test_lattice_sink_is_base_sink(self):
        """LatticeSink should inherit from BaseSink."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)
        assert isinstance(sink, BaseSink)

    def test_lattice_sink_requires_client(self):
        """LatticeSink should require a client in constructor."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)
        assert sink.client is mock_client


class TestLatticeSinkCotParsing:
    """Test CoT XML parsing and conversion."""

    def test_parses_drone_cot_to_lattice_format(self):
        """Should parse CoT XML and convert to Lattice entity format."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        # Should have called client.publish_entity
        assert mock_client.publish_entity.called

        # Extract entity data
        entity_data = mock_client.publish_entity.call_args[1]

        # Verify entity format
        assert entity_data['entity_id'] == 'drone-123'
        assert entity_data['latitude'] == 37.7749
        assert entity_data['longitude'] == -122.4194
        assert entity_data['altitude'] == 100.0

    def test_extracts_drone_metadata(self):
        """Should extract callsign and other metadata."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        entity_data = mock_client.publish_entity.call_args[1]

        assert 'callsign' in entity_data
        assert entity_data['callsign'] == 'DRONE-ABC'

    def test_sets_entity_type_for_drone(self):
        """Should set appropriate entity type for drones."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        entity_data = mock_client.publish_entity.call_args[1]

        # Should identify as drone/UAV
        assert 'entity_type' in entity_data
        assert entity_data['entity_type'] in ['drone', 'uav', 'unmanned']

    def test_handles_minimal_cot(self):
        """Should handle CoT with minimal elements."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.publish_cot_event(MINIMAL_COT)

        entity_data = mock_client.publish_entity.call_args[1]

        # Should have required fields
        assert entity_data['entity_id'] == 'drone-minimal'
        assert entity_data['latitude'] == 37.0
        assert entity_data['longitude'] == -122.0
        assert entity_data['altitude'] == 50.0


class TestLatticeSinkPublish:
    """Test Lattice entity publishing."""

    def test_publishes_to_client(self):
        """Should call client.publish_entity."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.publish_cot_event(SAMPLE_DRONE_COT)

        mock_client.publish_entity.assert_called_once()

    def test_publishes_multiple_entities(self):
        """Can publish multiple different entities."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        cot1 = b'<event uid="drone-1" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z"><point lat="1.0" lon="2.0" hae="3.0" ce="4.0" le="5.0"/></event>'
        cot2 = b'<event uid="drone-2" type="a-u-A-M-F-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z"><point lat="10.0" lon="20.0" hae="30.0" ce="40.0" le="50.0"/></event>'

        sink.publish_cot_event(cot1)
        sink.publish_cot_event(cot2)

        assert mock_client.publish_entity.call_count == 2

        # Verify entity IDs
        call1_data = mock_client.publish_entity.call_args_list[0][1]
        call2_data = mock_client.publish_entity.call_args_list[1][1]
        assert call1_data['entity_id'] == 'drone-1'
        assert call2_data['entity_id'] == 'drone-2'

    def test_handles_invalid_xml(self):
        """Should handle invalid XML gracefully."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        invalid_cot = b'<invalid xml'

        with pytest.raises(Exception):  # XML parsing error
            sink.publish_cot_event(invalid_cot)

    def test_handles_client_errors(self):
        """Should propagate client publish errors."""
        mock_client = Mock()
        mock_client.publish_entity.side_effect = ConnectionError("Lattice API error")

        sink = LatticeSink(mock_client)

        with pytest.raises(ConnectionError, match="Lattice API error"):
            sink.publish_cot_event(SAMPLE_DRONE_COT)


class TestLatticeSinkMarkInactive:
    """Test mark_inactive method."""

    def test_mark_inactive_expires_entity(self):
        """mark_inactive should expire entity in Lattice."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.mark_inactive("drone-abc-123")

        # Should call client to mark entity as expired/inactive
        mock_client.expire_entity.assert_called_once_with(entity_id="drone-abc-123")

    def test_mark_inactive_multiple_entities(self):
        """Can mark multiple entities as inactive."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.mark_inactive("drone-1")
        sink.mark_inactive("drone-2")
        sink.mark_inactive("drone-3")

        assert mock_client.expire_entity.call_count == 3


class TestLatticeSinkClose:
    """Test close method."""

    def test_close_calls_client_close(self):
        """close should call client.close()."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        sink.close()

        mock_client.close.assert_called_once()

    def test_close_handles_missing_client_close(self):
        """close should handle client without close method."""
        mock_client = Mock(spec=['publish_entity', 'expire_entity'])  # No close
        sink = LatticeSink(mock_client)

        # Should not raise error
        sink.close()


class TestLatticeSinkIntegration:
    """Integration-style tests."""

    def test_full_lifecycle(self):
        """Test full lifecycle: publish entities, mark inactive, close."""
        mock_client = Mock()
        sink = LatticeSink(mock_client)

        # Publish some entities
        sink.publish_cot_event(SAMPLE_DRONE_COT)
        sink.publish_cot_event(MINIMAL_COT)

        # Mark one as inactive
        sink.mark_inactive("drone-123")

        # Close
        sink.close()

        # Verify all calls
        assert mock_client.publish_entity.call_count == 2
        mock_client.expire_entity.assert_called_once()
        mock_client.close.assert_called_once()
