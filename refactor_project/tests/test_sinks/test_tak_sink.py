"""Tests for TAK Sink (CoT passthrough)."""

import pytest
from unittest.mock import Mock, call
from refactor_project.sinks.tak_sink import TakSink
from refactor_project.sinks.base_sink import BaseSink


class TestTakSinkInterface:
    """Test TAK Sink implements BaseSink correctly."""

    def test_tak_sink_is_base_sink(self):
        """TakSink should inherit from BaseSink."""
        mock_client = Mock()
        sink = TakSink(mock_client)
        assert isinstance(sink, BaseSink)

    def test_tak_sink_requires_client(self):
        """TakSink should require a client in constructor."""
        mock_client = Mock()
        sink = TakSink(mock_client)
        assert sink.client is mock_client


class TestTakSinkPublish:
    """Test CoT event publishing."""

    def test_publish_cot_event_sends_to_client(self):
        """publish_cot_event should send CoT XML to client."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        cot_xml = b'<event version="2.0">test</event>'
        sink.publish_cot_event(cot_xml)

        # Should call client's send method
        mock_client.send.assert_called_once_with(cot_xml)

    def test_publish_multiple_events(self):
        """Can publish multiple CoT events."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        cot1 = b'<event>event1</event>'
        cot2 = b'<event>event2</event>'
        cot3 = b'<event>event3</event>'

        sink.publish_cot_event(cot1)
        sink.publish_cot_event(cot2)
        sink.publish_cot_event(cot3)

        assert mock_client.send.call_count == 3
        mock_client.send.assert_has_calls([
            call(cot1),
            call(cot2),
            call(cot3)
        ])

    def test_publish_preserves_cot_xml_unchanged(self):
        """TAK Sink should pass CoT XML through unchanged (passthrough)."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        # Complex CoT XML
        cot_xml = b'''<event version="2.0" uid="test-123" type="a-u-A-M-H-Q" time="2025-11-16T12:00:00Z" start="2025-11-16T12:00:00Z" stale="2025-11-16T12:01:00Z" how="m-g">
<point lat="37.7749" lon="-122.4194" hae="100.0" ce="35.0" le="25.0"/>
<detail>
  <track course="180.0" speed="15.5"/>
  <remarks>Test drone</remarks>
</detail>
</event>'''

        sink.publish_cot_event(cot_xml)

        # Should send exact same bytes
        mock_client.send.assert_called_once_with(cot_xml)

    def test_publish_handles_client_errors(self):
        """TAK Sink should propagate client errors."""
        mock_client = Mock()
        mock_client.send.side_effect = ConnectionError("Network error")

        sink = TakSink(mock_client)
        cot_xml = b'<event>test</event>'

        with pytest.raises(ConnectionError, match="Network error"):
            sink.publish_cot_event(cot_xml)


class TestTakSinkMarkInactive:
    """Test mark_inactive method."""

    def test_mark_inactive_sends_deletion_event(self):
        """mark_inactive should send a CoT deletion event."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        sink.mark_inactive("drone-abc-123")

        # Should send a CoT deletion message
        mock_client.send.assert_called_once()
        sent_cot = mock_client.send.call_args[0][0]

        # Verify it's CoT XML
        assert b'<event' in sent_cot
        assert b'drone-abc-123' in sent_cot
        # Should have type ending in -r-r-r (removal/retired)
        assert b't-x-d-d' in sent_cot  # TAK deletion type

    def test_mark_inactive_multiple_drones(self):
        """Can mark multiple drones as inactive."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        sink.mark_inactive("drone-1")
        sink.mark_inactive("drone-2")
        sink.mark_inactive("drone-3")

        assert mock_client.send.call_count == 3


class TestTakSinkClose:
    """Test close method."""

    def test_close_calls_client_close(self):
        """close should call client.close()."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        sink.close()

        mock_client.close.assert_called_once()

    def test_close_handles_missing_client_close(self):
        """close should handle client without close method."""
        mock_client = Mock(spec=[])  # No close method
        sink = TakSink(mock_client)

        # Should not raise error
        sink.close()


class TestTakSinkIntegration:
    """Integration-style tests."""

    def test_full_lifecycle(self):
        """Test full lifecycle: publish events, mark inactive, close."""
        mock_client = Mock()
        sink = TakSink(mock_client)

        # Publish some events
        sink.publish_cot_event(b'<event uid="drone-1">test1</event>')
        sink.publish_cot_event(b'<event uid="drone-2">test2</event>')

        # Mark one as inactive
        sink.mark_inactive("drone-1")

        # Close
        sink.close()

        # Verify all calls happened
        assert mock_client.send.call_count == 3  # 2 publishes + 1 deletion
        mock_client.close.assert_called_once()
