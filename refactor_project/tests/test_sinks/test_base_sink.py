"""Tests for BaseSink interface."""

import pytest
from abc import ABC
from refactor_project.sinks.base_sink import BaseSink


class TestBaseSinkInterface:
    """Test the BaseSink abstract interface."""

    def test_base_sink_is_abstract(self):
        """BaseSink should be an abstract base class."""
        assert issubclass(BaseSink, ABC)

    def test_cannot_instantiate_base_sink(self):
        """Cannot instantiate BaseSink directly."""
        with pytest.raises(TypeError):
            BaseSink()  # type: ignore

    def test_base_sink_has_publish_cot_event_method(self):
        """BaseSink should define publish_cot_event abstract method."""
        assert hasattr(BaseSink, 'publish_cot_event')
        assert getattr(BaseSink.publish_cot_event, '__isabstractmethod__', False)

    def test_base_sink_has_mark_inactive_method(self):
        """BaseSink should define mark_inactive method (not abstract)."""
        assert hasattr(BaseSink, 'mark_inactive')
        # This should NOT be abstract (has default implementation)
        assert not getattr(BaseSink.mark_inactive, '__isabstractmethod__', False)

    def test_base_sink_has_close_method(self):
        """BaseSink should define close method (not abstract)."""
        assert hasattr(BaseSink, 'close')
        # This should NOT be abstract (has default implementation)
        assert not getattr(BaseSink.close, '__isabstractmethod__', False)


class TestConcreteImplementation:
    """Test that concrete implementations work correctly."""

    def test_concrete_sink_must_implement_publish_cot_event(self):
        """Concrete sink must implement publish_cot_event."""

        class IncompleteSink(BaseSink):
            """Missing publish_cot_event implementation."""
            pass

        with pytest.raises(TypeError):
            IncompleteSink()  # type: ignore

    def test_minimal_concrete_sink_works(self):
        """Minimal concrete sink with just publish_cot_event works."""

        class MinimalSink(BaseSink):
            """Minimal working sink."""

            def __init__(self):
                self.events = []

            def publish_cot_event(self, cot_xml: bytes) -> None:
                self.events.append(cot_xml)

        sink = MinimalSink()
        assert sink is not None
        assert isinstance(sink, BaseSink)

    def test_concrete_sink_can_publish_cot_event(self):
        """Concrete sink can publish CoT events."""

        class TestSink(BaseSink):
            """Test sink implementation."""

            def __init__(self):
                self.events = []

            def publish_cot_event(self, cot_xml: bytes) -> None:
                self.events.append(cot_xml)

        sink = TestSink()
        cot_xml = b'<event>test</event>'
        sink.publish_cot_event(cot_xml)

        assert len(sink.events) == 1
        assert sink.events[0] == cot_xml

    def test_concrete_sink_can_override_mark_inactive(self):
        """Concrete sink can override mark_inactive."""

        class TestSink(BaseSink):
            """Test sink with mark_inactive override."""

            def __init__(self):
                self.inactive_uids = []

            def publish_cot_event(self, cot_xml: bytes) -> None:
                pass

            def mark_inactive(self, uid: str) -> None:
                self.inactive_uids.append(uid)

        sink = TestSink()
        sink.mark_inactive("test-123")

        assert len(sink.inactive_uids) == 1
        assert sink.inactive_uids[0] == "test-123"

    def test_concrete_sink_can_override_close(self):
        """Concrete sink can override close."""

        class TestSink(BaseSink):
            """Test sink with close override."""

            def __init__(self):
                self.closed = False

            def publish_cot_event(self, cot_xml: bytes) -> None:
                pass

            def close(self) -> None:
                self.closed = True

        sink = TestSink()
        assert not sink.closed
        sink.close()
        assert sink.closed

    def test_default_mark_inactive_does_nothing(self):
        """Default mark_inactive implementation does nothing (no error)."""

        class TestSink(BaseSink):
            """Test sink without mark_inactive override."""

            def publish_cot_event(self, cot_xml: bytes) -> None:
                pass

        sink = TestSink()
        # Should not raise an error
        sink.mark_inactive("test-123")

    def test_default_close_does_nothing(self):
        """Default close implementation does nothing (no error)."""

        class TestSink(BaseSink):
            """Test sink without close override."""

            def publish_cot_event(self, cot_xml: bytes) -> None:
                pass

        sink = TestSink()
        # Should not raise an error
        sink.close()
