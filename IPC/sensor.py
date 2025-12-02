#sends random density readings and prints server acks

import json, random, socket, sys, time

HOST, PORT = "127.0.0.1", 9009
SID = sys.argv[1] if len(sys.argv) > 1 else "S-001"

def main():
    sock = socket.create_connection((HOST, PORT))
    f = sock.makefile("rwb", buffering=0)
    print(f"[tcp] {SID} connected")
    try:
        while True:
            density = max(0.0, random.gauss(35, 10))
            msg = {"sensor_id": SID, "density": density}
            f.write((json.dumps(msg) + "\n").encode())
            ack = f.readline().decode().strip()
            if ack:
                print(f"[tcp] {SID} <- {ack}")
            time.sleep(0.5)
    finally:
        try: sock.close()
        except: pass

if __name__ == "__main__":
    main()

