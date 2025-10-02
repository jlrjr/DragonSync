# ZMQ Drone Logger

This script subscribes to a DragonSync (or compatible) ZeroMQ publisher, parses incoming drone Remote ID telemetry, and writes structured logs to a CSV file for later analysis or KML generation.

## Features
- Connects to a ZMQ telemetry stream (default `tcp://127.0.0.1:4224`).
- Extracts key Remote ID fields:
  - Core: `id`, `lat`, `lon`, `alt`, `speed`, `rssi`, `mac`, `description`, `pilot_lat`, `pilot_lon`
  - Extended: `home_lat`, `home_lon`, `ua_type`, `operator_id`, `op_status`, `height`, `direction`, `vspeed`, `freq`, etc.
- Per-drone **rate-limiting**:
  - Only logs if:
    - Enough time has passed (`--min-log-interval`, default 30s), OR
    - Drone moved ≥ `--min-move-m` (default 25m), OR
    - Altitude change ≥ `--min-alt-change` (default 5m), OR
    - Speed change ≥ `--min-speed-change` (default 1 m/s).
- ZMQ backpressure options:
  - `--rcv-hwm` to set receive buffer high-water mark.
  - `--conflate` to drop backlog and keep only the latest message.
- CSV output with consistent headers. Missing fields are logged as blanks.

## Usage

```bash
python3 logger.py \
  --zmq-host 127.0.0.1 \
  --zmq-port 4224 \
  --output-csv drone_log.csv \
  --min-log-interval 30 \
  --min-move-m 25 \
  --min-alt-change 5 \
  --min-speed-change 1
```

Optional flags:
- `--flush-interval 5` → flush to disk every 5 seconds
- `--rcv-hwm 1000` → limit queued messages
- `--conflate` → only keep most recent
- `--debug` → verbose logging

## Example CSV Header

```
timestamp,drone_id,lat,lon,alt,speed,rssi,mac,description,pilot_lat,pilot_lon,
home_lat,home_lon,ua_type,ua_type_name,operator_id_type,operator_id,op_status,
height,height_type,direction,vspeed,ew_dir,speed_multiplier,pressure_altitude,
vertical_accuracy,horizontal_accuracy,baro_accuracy,speed_accuracy,
timestamp_src,timestamp_accuracy,index,runtime,caa,freq
```

## Notes
- Logs only meaningful changes, reducing spam when Remote ID is chatty.
- Backwards-compatible with older DragonSync message shapes, but supports newer fields (home location, UA type, operator info, etc.).
- CSV timestamps are UTC write time (`timestamp`), with `timestamp_src` reflecting any source-provided telemetry timestamp if available.
