"""
Output adapters for various protocols

Sinks publish drone data to external systems:
- BaseSink: Abstract sink interface
- MqttSink: MQTT publishing
- LatticeSink: Lattice integration
- HaSink: Home Assistant specific logic
- TakSink: TAK server sink
"""

__all__ = []
