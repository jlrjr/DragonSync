"""Base sink interface for output adapters.

All sinks consume CoT XML (the universal format) and distribute to various endpoints.
Each sink is responsible for parsing/transforming CoT to its specific output format.
"""

from abc import ABC, abstractmethod


class BaseSink(ABC):
    """Abstract base class for all output sinks.

    Sinks consume CoT XML (bytes) as input and distribute to various endpoints:
    - TAK Sink: Passes CoT through to TAK server/multicast
    - MQTT Sink: Parses CoT → JSON for Home Assistant
    - Lattice Sink: Parses CoT → custom API format

    This design enables:
    - Universal input format (all sinks accept CoT XML)
    - Easy addition of new sources (sinks don't change)
    - Clean separation of concerns (parsing vs. I/O)
    """

    @abstractmethod
    def publish_cot_event(self, cot_xml: bytes) -> None:
        """Publish a CoT event to the sink's endpoint.

        Args:
            cot_xml: CoT XML event as bytes (universal format).

        Raises:
            Various exceptions depending on sink implementation
            (network errors, parsing errors, etc.)

        Note:
            Implementations should parse the CoT XML to extract needed data,
            then convert to the sink's specific output format.
        """
        pass

    def mark_inactive(self, uid: str) -> None:
        """Mark an entity as inactive (optional).

        Args:
            uid: Unique identifier of the entity (CoT UID).

        Note:
            Default implementation does nothing. Sinks can override
            to send deletion messages or inactive status updates.
        """
        pass

    def close(self) -> None:
        """Close the sink and cleanup resources (optional).

        Note:
            Default implementation does nothing. Sinks can override
            to close connections, flush buffers, etc.
        """
        pass
