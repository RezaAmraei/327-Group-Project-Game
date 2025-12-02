#accepts multiple sensor clients and keeps a 30s rolling avg of density
import json, socket, threading, time
from collections import deque

HOST, PORT = "127.0.0.1", 9009
WINDOW = 30  # seconds

samples = deque()       # (timestamp, density)
lock = threading.Lock() # protect samples

def clean_old(now):
    # remove samples older than 30s
    while samples and now - samples[0][0] > WINDOW:
        samples.popleft()

def avg_30s():
    # compute average over current window
    if not samples:
        return 0.0
    total = sum(d for _, d in samples)
    return total / len(samples)

def handle(conn, addr):
    print("[tcp] connected", addr)
    f = conn.makefile("rwb", buffering=0)
    try:
        while True:
            line = f.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode().strip())
                density = float(msg["density"])
                now = time.time()
                with lock:
                    clean_old(now)
                    samples.append((now, density))
                    a = avg_30s()
                reply = {"ok": True, "rolling_avg_30s": a}
                f.write((json.dumps(reply) + "\n").encode())
            except Exception as e:
                f.write((json.dumps({"ok": False, "error": str(e)}) + 
"\n").encode())
    finally:
        print("[tcp] disconnected", addr)
        try: conn.close()
        except: pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[tcp] listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle, args=(conn, addr), 
daemon=True).start()
    finally:
        s.close()

if __name__ == "__main__":
    main()

