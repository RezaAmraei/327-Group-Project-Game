#sends density every .5s and prints ack

import json, random, socket, sys, time

HOST, PORT = "127.0.0.1", 9010
SID = sys.argv[1] if len(sys.argv) > 1 else "U-001"

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[udp] {SID} started")
    while True:
        density = max(0.0, random.gauss(35, 10))
        msg = {"sensor_id": SID, "density": density}
        s.sendto(json.dumps(msg).encode(), (HOST, PORT))
        try:
            s.settimeout(1.0)
            data, _ = s.recvfrom(4096)
            print(f"[udp] {SID} <- {data.decode().strip()}")
        except socket.timeout:
            print(f"[udp] {SID} no ack (ok for udp)")
        time.sleep(0.5)

if __name__ == "__main__":
    main()

