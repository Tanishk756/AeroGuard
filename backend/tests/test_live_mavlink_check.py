"""Live MAVLink Telemetry Packet Inspection Tool for ArduCopter SITL."""

import time
from pymavlink import mavutil

def verify_live_mavlink_stream(endpoint="udpin:127.0.0.1:14550", timeout_sec=10):
    print(f"Connecting to live MAVLink stream on {endpoint}...")
    conn = mavutil.mavlink_connection(endpoint)
    
    packet_counts = {
        "HEARTBEAT": 0,
        "ATTITUDE": 0,
        "GLOBAL_POSITION_INT": 0,
        "SYS_STATUS": 0,
        "GPS_RAW_INT": 0
    }
    
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        msg = conn.recv_match(blocking=True, timeout=1.0)
        if msg:
            mtype = msg.get_type()
            if mtype in packet_counts:
                packet_counts[mtype] += 1
                print(f"Received [{mtype}]: {msg.to_dict()}")
            if all(count > 0 for count in packet_counts.values()):
                print("Successfully received ALL required MAVLink packet types!")
                break
                
    return packet_counts

if __name__ == "__main__":
    counts = verify_live_mavlink_stream()
    print("Final Packet Counts:", counts)
