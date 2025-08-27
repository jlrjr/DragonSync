import json
from telemetry_parser import parse_drone_info

UA = {
    0: 'No UA type defined',
    1: 'Aeroplane/Airplane (Fixed wing)',
    2: 'Helicopter or Multirotor',
    15: 'Other type',
}

def test_dji_list_with_freq_and_serial():
    msg = [
        {"Basic ID": {"id_type": "Serial Number (ANSI/CTA-2063-A)", "id": "SN123", "ua_type": 2, "MAC": "AA:BB", "RSSI": -65}},
        {"Location/Vector Message": {"latitude": 10.0, "longitude": 20.0, "speed": 5.0, "vert_speed": -1.0, "geodetic_altitude": 120.0, "height_agl": 30.0}},
        {"Frequency Message": {"frequency": 5805000000.0}},  # 5.805 GHz
        {"Self-ID Message": {"text": "DJI Phantom"}}
    ]
    out = parse_drone_info(msg, UA)
    assert out["id"] == "SN123"
    assert out["ua_type"] == 2 and out["ua_type_name"].lower().startswith("helicopter")
    assert out["lat"] == 10.0 and out["lon"] == 20.0
    assert out["freq"] == 5805000000.0

def test_esp32_dict_caa_only_no_freq():
    msg = {
        "Basic ID": {"id_type": "CAA Assigned Registration ID", "id": "CAA-XYZ", "ua_type": "Other type", "MAC": "CC:DD", "RSSI": -70},
        "Location/Vector Message": {"latitude": 1.0, "longitude": 2.0, "speed": 0.5, "vert_speed": 0.0, "geodetic_altitude": 50.0, "height_agl": 5.0},
        "Self-ID Message": {"text": "Some RID"}
    }
    out = parse_drone_info(msg, UA)
    assert out["caa"] == "CAA-XYZ"
    assert out["freq"] is None or "freq" not in out
