"""
Base parser interface for telemetry parsers.

Defines the contract for all telemetry parsers.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

# Generic type for parsed output
T = TypeVar('T')


class BaseParser(ABC):
    """
    Abstract base class for telemetry parsers.

    All parsers must implement the parse() method to convert
    raw messages into domain models.
    """

    @abstractmethod
    def parse(self, message: Any) -> Optional[T]:
        """
        Parse raw message into a domain model.

        Args:
            message: Raw message data (format depends on parser)

        Returns:
            Parsed domain model instance, or None if parsing fails

        Raises:
            May raise exceptions for critical parsing errors,
            but should generally return None for invalid messages
        """
        pass

    def validate(self, message: Any) -> bool:
        """
        Validate message format before parsing.

        Args:
            message: Raw message data

        Returns:
            True if message is valid and can be parsed

        Note:
            This is optional - parsers can override if they need
            validation before parsing. Default returns True.
        """
        return message is not None
