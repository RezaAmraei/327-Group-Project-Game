#listens for density packets and sends back rolling avg 
import json, socket, time
from collections import deque

HOST, PORT = "127.0.0.1", 9010
WINDOW = 30
samples = deque()

def clean_old(now):
    while samples and now - samples[0][0] > WINDOW:
        samples.popleft()

def avg_30s():
    if not samples:
        return 0.0
    return sum(d for _, d in samples) / len(samples)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, PORT))
    print(f"[udp] listening on {HOST}:{PORT}")
    while True:
        data, addr = s.recvfrom(4096)
        try:
            msg = json.loads(data.decode().strip())
            density = float(msg["density"])
            now = time.time()
            clean_old(now)
            samples.append((now, density))
            reply = {"ok": True, "rolling_avg_30s": avg_30s()}
            s.sendto((json.dumps(reply) + "\n").encode(), addr)
        except Exception as e:
            s.sendto((json.dumps({"ok": False, "error": str(e)}) + 
"\n").encode(), addr)

if __name__ == "__main__":
    main()

