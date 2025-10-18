#!/usr/bin/env python3
"""Simple ZMQ listener to debug what's being published on port 4224"""
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:4224")
socket.subscribe("")  # Subscribe to all messages

print("Listening on tcp://127.0.0.1:4224...")
print("Press Ctrl+C to stop\n")

message_count = 0
try:
    while True:
        # Try both recv_json() and recv_string() to see which works
        try:
            raw = socket.recv_json(flags=zmq.NOBLOCK)
            message_count += 1
            print(f"\n=== Message #{message_count} (recv_json) ===")
            print(json.dumps(raw, indent=2))
        except zmq.Again:
            # No message available, wait a bit
            import time
            time.sleep(0.1)
        except Exception as e:
            print(f"recv_json failed: {e}")
            # Try as string instead
            try:
                raw_str = socket.recv_string()
                message_count += 1
                print(f"\n=== Message #{message_count} (recv_string) ===")
                print(raw_str)
            except Exception as e2:
                print(f"recv_string also failed: {e2}")

except KeyboardInterrupt:
    print(f"\n\nReceived {message_count} messages total")
finally:
    socket.close()
    context.term()
