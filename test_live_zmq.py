#!/usr/bin/env python3
"""
Live ZMQ telemetry testing for refactored DragonSync parsers
Connect to real drone telemetry stream and parse with new code
"""

import sys
import time
import json
import argparse
sys.path.insert(0, '/home/user/DragonSync')

try:
    import zmq
except ImportError:
    print("❌ ZMQ not installed. Install with: pip install pyzmq")
    sys.exit(1)

from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.tests.fixtures.sample_messages import UA_TYPE_MAPPING

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Test refactored DragonSync parser with live ZMQ stream"
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='ZMQ host address (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5555,
        help='ZMQ port (default: 5555)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=0,
        help='Stop after N seconds (0 = run forever)'
    )
    parser.add_argument(
        '--max-drones',
        type=int,
        default=0,
        help='Stop after N drones parsed (0 = no limit)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed drone information'
    )
    parser.add_argument(
        '--save',
        type=str,
        help='Save parsed results to JSON file'
    )
    parser.add_argument(
        '--show-errors',
        action='store_true',
        help='Display parsing errors and raw message data'
    )

    return parser.parse_args()

def format_drone_info(drone, verbose=False):
    """Format drone information for display"""
    lines = []
    lines.append(f"   ID: {drone.id}")
    lines.append(f"   Position: {drone.lat:.6f}, {drone.lon:.6f}, {drone.alt:.1f}m")
    lines.append(f"   Speed: {drone.speed:.1f} m/s (vertical: {drone.vspeed:.1f} m/s)")

    if verbose:
        lines.append(f"   Height AGL: {drone.height:.1f}m")
        lines.append(f"   Pilot: {drone.pilot_lat:.6f}, {drone.pilot_lon:.6f}")
        lines.append(f"   Type: {drone.ua_type}")
        lines.append(f"   MAC: {drone.mac}, RSSI: {drone.rssi}")

        if drone.caa_id:
            lines.append(f"   CAA ID: {drone.caa_id}")
        if drone.description:
            lines.append(f"   Description: {drone.description}")
        if drone.operator_id:
            lines.append(f"   Operator: {drone.operator_id}")

    return "\n".join(lines)

def main():
    """Main testing loop"""
    args = parse_args()

    print("🎯 DragonSync Refactor - Live ZMQ Testing")
    print("=" * 70)
    print(f"   ZMQ Connection: tcp://{args.host}:{args.port}")
    print(f"   Timeout: {args.timeout}s" if args.timeout else "   Timeout: None (run forever)")
    print(f"   Max Drones: {args.max_drones}" if args.max_drones else "   Max Drones: Unlimited")
    print(f"   Verbose: {'Yes' if args.verbose else 'No'}")
    print("=" * 70)
    print()

    # Setup ZMQ connection
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://{args.host}:{args.port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for recv

    # Create parser
    parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)

    # Statistics
    drone_count = 0
    error_count = 0
    start_time = time.time()
    results = []
    unique_drones = set()

    print("📡 Listening for drone telemetry... (Ctrl+C to stop)")
    print()

    try:
        while True:
            # Check timeout
            if args.timeout > 0 and (time.time() - start_time) > args.timeout:
                print(f"\n⏱️  Timeout reached ({args.timeout}s)")
                break

            # Check max drones
            if args.max_drones > 0 and drone_count >= args.max_drones:
                print(f"\n🎯 Max drones reached ({args.max_drones})")
                break

            try:
                # Receive ZMQ message
                message = socket.recv()

                # Try to parse as JSON
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    # Maybe it's already a Python dict (pickled?)
                    data = message

                # Parse with refactored parser
                drone = parser.parse(data)

                if drone:
                    drone_count += 1
                    unique_drones.add(drone.id)

                    print(f"✅ Drone #{drone_count} (unique: {len(unique_drones)})")
                    print(format_drone_info(drone, verbose=args.verbose))
                    print()

                    # Save result
                    if args.save:
                        results.append({
                            'timestamp': time.time(),
                            'drone_num': drone_count,
                            'id': drone.id,
                            'lat': drone.lat,
                            'lon': drone.lon,
                            'alt': drone.alt,
                            'speed': drone.speed,
                            'vspeed': drone.vspeed,
                            'ua_type': drone.ua_type,
                            'mac': drone.mac,
                            'rssi': drone.rssi,
                        })

                else:
                    error_count += 1
                    if args.show_errors:
                        print(f"❌ Parse Error #{error_count}")
                        print(f"   Raw data (first 200 chars): {str(data)[:200]}")
                        print()

            except zmq.Again:
                # Timeout waiting for message, continue
                continue

            except Exception as e:
                error_count += 1
                if args.show_errors:
                    print(f"💥 Exception #{error_count}: {e}")
                    print()

    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")

    finally:
        # Cleanup
        socket.close()
        context.term()

        # Statistics
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print("📊 Statistics")
        print("=" * 70)
        print(f"   Runtime: {elapsed:.1f}s")
        print(f"   Total Messages: {drone_count + error_count}")
        print(f"   Successfully Parsed: {drone_count}")
        print(f"   Parse Errors: {error_count}")
        print(f"   Success Rate: {drone_count/(drone_count+error_count)*100:.1f}%" if (drone_count + error_count) > 0 else "   Success Rate: N/A")
        print(f"   Unique Drones: {len(unique_drones)}")

        if drone_count > 0:
            print(f"   Throughput: {drone_count/elapsed:.2f} drones/sec")

        print("=" * 70)

        # Save results to file
        if args.save and results:
            with open(args.save, 'w') as f:
                json.dump({
                    'metadata': {
                        'start_time': start_time,
                        'end_time': time.time(),
                        'elapsed_seconds': elapsed,
                        'total_drones': drone_count,
                        'unique_drones': len(unique_drones),
                        'parse_errors': error_count,
                        'zmq_host': args.host,
                        'zmq_port': args.port,
                    },
                    'drones': results,
                }, f, indent=2)

            print(f"\n💾 Results saved to: {args.save}")
            print(f"   ({len(results)} drone records)")

        # Show unique drone IDs
        if unique_drones and args.verbose:
            print("\n📋 Unique Drone IDs:")
            for drone_id in sorted(unique_drones):
                print(f"   - {drone_id}")

if __name__ == "__main__":
    main()
