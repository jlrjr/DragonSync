"""
Cursor on Target (CoT) message generation

CoT messaging components:
- CotMessenger: CoT message sending
- CotGenerator: CoT XML generation
- CotTypes: CoT type mappings
- MulticastHandler: Multicast CoT handling
"""

from refactor_project.messaging.cot_generator import CotGenerator

__all__ = ["CotGenerator"]
