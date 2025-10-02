#!/usr/bin/env python3
import argparse
import logging
import time
import zmq
import csv
from datetime import datetime
from math import radians, sin, cos, asin, sqrt

def haversine_m(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return 0.0
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def get_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def parse_drone_message(message, logger):
    """
    Tolerates old/new DragonSync shapes. Returns a dict with base + extended fields.
    """
    def merge_into(dst, src):
        for k, v in src.items():
            if v is None:
                continue
            dst[k] = v

    def parse_one(obj):
        if not isinstance(obj, dict):
            return {}
        out = {}

        aux = obj.get("AUX_ADV_IND")
        if isinstance(aux, dict) and "rssi" in aux:
            out["rssi"] = aux["rssi"]
        aext = obj.get("aext")
        if isinstance(aext, dict):
            adv = aext.get("AdvA")
            if isinstance(adv, str):
                out["mac"] = adv.split()[0]

        bid = obj.get("Basic ID")
        if isinstance(bid, dict):
            id_type = bid.get("id_type")
            out["mac"]  = bid.get("MAC", out.get("mac", ""))
            out["rssi"] = bid.get("RSSI", out.get("rssi", 0.0))
            if id_type in ("Serial Number (ANSI/CTA-2063-A)", "CAA Assigned Registration ID"):
                out.setdefault("id", bid.get("id", "unknown"))
            out["id_type"] = id_type

        lvm = obj.get("Location/Vector Message")
        if isinstance(lvm, dict):
            out["lat"]    = get_float(lvm.get("latitude", 0.0))
            out["lon"]    = get_float(lvm.get("longitude", 0.0))
            out["speed"]  = get_float(lvm.get("speed", 0.0))
            out["vspeed"] = get_float(lvm.get("vert_speed", 0.0))
            out["alt"]    = get_float(lvm.get("geodetic_altitude", 0.0))
            out["height"] = get_float(lvm.get("height_agl", 0.0))
            out["direction"] = get_float(lvm.get("direction"), None)
            out["pressure_altitude"] = get_float(lvm.get("pressure_altitude"), None)
            out["vertical_accuracy"]   = lvm.get("vertical_accuracy")
            out["horizontal_accuracy"] = lvm.get("horizontal_accuracy")
            out["baro_accuracy"]       = lvm.get("baro_accuracy")
            out["speed_accuracy"]      = lvm.get("speed_accuracy")
            out["height_type"]         = lvm.get("height_type")
            out["timestamp"]           = lvm.get("timestamp")
            out["timestamp_accuracy"]  = lvm.get("timestamp_accuracy")
            out["ew_dir"]              = lvm.get("ew_dir")
            out["speed_multiplier"]    = lvm.get("speed_multiplier")

        sid = obj.get("Self-ID Message")
        if isinstance(sid, dict):
            out["description"] = sid.get("text", "")

        sysm = obj.get("System Message")
        if isinstance(sysm, dict):
            out["pilot_lat"] = get_float(sysm.get("latitude", 0.0))
            out["pilot_lon"] = get_float(sysm.get("longitude", 0.0))
            out["home_lat"]  = get_float(sysm.get("home_lat", 0.0))
            out["home_lon"]  = get_float(sysm.get("home_lon", 0.0))
            out["operator_id_type"] = sysm.get("operator_id_type")
            out["operator_id"]      = sysm.get("operator_id")
            out["op_status"]        = sysm.get("op_status")
            out["ua_type"]          = sysm.get("ua_type")
            out["ua_type_name"]     = sysm.get("ua_type_name")

        # flat extras sometimes present
        out["freq"]   = obj.get("freq", out.get("freq"))
        out["caa"]    = obj.get("caa",  out.get("caa"))
        out["index"]  = obj.get("index", out.get("index"))
        out["runtime"]= obj.get("runtime", out.get("runtime"))

        return out

    drone_info = {}
    if isinstance(message, list):
        for item in message:
            merge_into(drone_info, parse_one(item))
    elif isinstance(message, dict):
        merge_into(drone_info, parse_one(message))
    else:
        logger.error("Unexpected message format; expected dict or list.")
        return None

    if 'id' not in drone_info or not drone_info['id']:
        logger.debug("No drone ID found; skipping.")
        return None
    if not str(drone_info['id']).startswith('drone-'):
        drone_info['id'] = f"drone-{drone_info['id']}"

    # base defaults
    drone_info.setdefault('lat', 0.0)
    drone_info.setdefault('lon', 0.0)
    drone_info.setdefault('alt', 0.0)
    drone_info.setdefault('speed', 0.0)
    drone_info.setdefault('rssi', 0.0)
    drone_info.setdefault('description', "")
    drone_info.setdefault('pilot_lat', 0.0)
    drone_info.setdefault('pilot_lon', 0.0)
    drone_info.setdefault('mac', "")

    # extended defaults
    for k in [
        "home_lat","home_lon","ua_type","ua_type_name","operator_id_type","operator_id","op_status",
        "height","height_type","direction","vspeed","ew_dir","speed_multiplier","pressure_altitude",
        "vertical_accuracy","horizontal_accuracy","baro_accuracy","speed_accuracy",
        "timestamp","timestamp_accuracy","index","runtime","caa","freq"
    ]:
        drone_info.setdefault(k, "")

    return drone_info

def should_log(prev, cur, th):
    if prev is None:
        return True
    dist = haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])
    if th["min_move_m"] and dist >= th["min_move_m"]:
        return True
    if th["min_alt_change"] and abs(cur["alt"] - prev["alt"]) >= th["min_alt_change"]:
        return True
    if th["min_speed_change"] and abs(cur["speed"] - prev["speed"]) >= th["min_speed_change"]:
        return True
    if th["min_log_interval"] and (cur["t"] - prev["t"]) >= th["min_log_interval"]:
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="ZMQ logger (rate-limited) with home/metadata columns.")
    parser.add_argument("--zmq-host", default="127.0.0.1")
    parser.add_argument("--zmq-port", type=int, default=4224)
    parser.add_argument("--output-csv", default="drone_log.csv")
    parser.add_argument("--flush-interval", type=float, default=5.0)
    parser.add_argument("--rcv-hwm", type=int, default=0, help="0=unlimited")
    parser.add_argument("--conflate", action="store_true", help="Keep only latest (drop backlog)")

    # Per-drone throttling
    parser.add_argument("--min-log-interval", type=float, default=30.0)
    parser.add_argument("--min-move-m", type=float, default=25.0)
    parser.add_argument("--min-alt-change", type=float, default=5.0)
    parser.add_argument("--min-speed-change", type=float, default=1.0)

    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info(f"Connecting to ZMQ at tcp://{args.zmq_host}:{args.zmq_port}")

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    if args.rcv_hwm is not None:
        socket.setsockopt(zmq.RCVHWM, args.rcv_hwm)
    if args.conflate:
        socket.setsockopt(zmq.CONFLATE, 1)
    socket.connect(f"tcp://{args.zmq_host}:{args.zmq_port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    headers = [
        # base
        "timestamp","drone_id","lat","lon","alt","speed","rssi","mac","description","pilot_lat","pilot_lon",
        # extended (always included now)
        "home_lat","home_lon","ua_type","ua_type_name","operator_id_type","operator_id","op_status",
        "height","height_type","direction","vspeed","ew_dir","speed_multiplier","pressure_altitude",
        "vertical_accuracy","horizontal_accuracy","baro_accuracy","speed_accuracy",
        "timestamp_src","timestamp_accuracy","index","runtime","caa","freq"
    ]

    csv_file = open(args.output_csv, 'a', newline='')
    csv_writer = csv.writer(csv_file)
    if csv_file.tell() == 0:
        csv_writer.writerow(headers)

    buf = []
    last_flush = time.time()
    last_logged = {}  # drone_id -> snapshot

    th = {
        "min_log_interval": max(0.0, args.min_log_interval),
        "min_move_m": max(0.0, args.min_move_m),
        "min_alt_change": max(0.0, args.min_alt_change),
        "min_speed_change": max(0.0, args.min_speed_change),
    }

    try:
        while True:
            socks = dict(poller.poll(timeout=1000))
            if socket in socks and socks[socket] == zmq.POLLIN:
                try:
                    raw = socket.recv_json()
                except Exception as e:
                    logger.warning(f"recv_json failed: {e}")
                    continue

                parsed = parse_drone_message(raw, logger)
                if not parsed:
                    continue

                drone_id = parsed["id"]
                now_ts = time.time()
                cur = {"t": now_ts, "lat": parsed["lat"], "lon": parsed["lon"], "alt": parsed["alt"], "speed": parsed["speed"]}
                prev = last_logged.get(drone_id)

                if should_log(prev, cur, th):
                    row = [
                        datetime.utcnow().isoformat(),
                        drone_id,
                        parsed["lat"], parsed["lon"], parsed["alt"], parsed["speed"],
                        parsed["rssi"], parsed["mac"], parsed["description"],
                        parsed["pilot_lat"], parsed["pilot_lon"],
                        parsed["home_lat"], parsed["home_lon"], parsed["ua_type"], parsed["ua_type_name"],
                        parsed["operator_id_type"], parsed["operator_id"], parsed["op_status"],
                        parsed["height"], parsed["height_type"], parsed["direction"], parsed["vspeed"],
                        parsed["ew_dir"], parsed["speed_multiplier"], parsed["pressure_altitude"],
                        parsed["vertical_accuracy"], parsed["horizontal_accuracy"], parsed["baro_accuracy"],
                        parsed["speed_accuracy"],
                        parsed["timestamp"], parsed["timestamp_accuracy"], parsed["index"], parsed["runtime"],
                        parsed["caa"], parsed["freq"]
                    ]
                    buf.append(row)
                    last_logged[drone_id] = cur
                    logger.debug(f"Queued log for {drone_id}")

            now = time.time()
            if (now - last_flush) >= args.flush_interval and buf:
                logger.debug(f"Flushing {len(buf)} rows")
                csv_writer.writerows(buf)
                csv_file.flush()
                buf.clear()
                last_flush = now

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        if buf:
            csv_writer.writerows(buf)
        csv_file.flush()
        csv_file.close()
        try:
            socket.close(0)
        finally:
            context.term()

if __name__ == "__main__":
    main()
