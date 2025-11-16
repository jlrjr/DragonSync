"""
Output adapters for various protocols.

Sinks consume CoT XML (universal format) and distribute to external systems:
- BaseSink: Abstract sink interface (publish_cot_event)
- TakSink: TAK server/multicast (CoT passthrough)
- MqttSink: MQTT/Home Assistant (CoT → JSON)
- LatticeSink: Lattice integration (CoT → custom format)
"""

from refactor_project.sinks.base_sink import BaseSink
from refactor_project.sinks.tak_sink import TakSink
from refactor_project.sinks.mqtt_sink import MqttSink
from refactor_project.sinks.lattice_sink import LatticeSink

__all__ = ['BaseSink', 'TakSink', 'MqttSink', 'LatticeSink']
