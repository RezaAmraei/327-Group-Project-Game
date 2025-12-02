'''
The goal of the addition in this part 4 
'''
import asyncio, json, socket, sys, time, random
from collections import deque
from contextlib import suppress

DISCOVERY_PORT = 9999 # udp discovery
BEACON_SEC     = 2.0 #sening a beacon out every 2 seconds
PEER_TTL_SEC   = 8.0 # forget peers not seen in 8 seconds

DEFAULT_TCP_PORT = 5000        # tcp port used for data exchange
WINDOW_SEC       = 30          # rolling average window size in seconds


'''
Keeps a rolling window of 30 seconds of density and then computes their average 
'''
class RollingAvg30s:
    def __init__(self, window_sec=WINDOW_SEC):
        self.window = window_sec
        self.samples = deque()   # (ts, density)
    #this gets rid of any samples who're older than the  30 second window  
    def clean(self, now=None):
        if now is None:
            now = time.time()
        while self.samples and now - self.samples[0][0] > self.window:
            self.samples.popleft()
    #just adding those new samples in
    def add(self, density, now=None):
        if now is None:
            now = time.time()
        self.clean(now)
        self.samples.append((now, float(density)))
    #Averaging out the samples of those recent balues 
    def avg(self, now=None):
        self.clean(now)
        if not self.samples:
            return 0.0
        return sum(d for _, d in self.samples) / len(self.samples)

class Peer:
    def __init__(self, name, tcp_port=DEFAULT_TCP_PORT):
        self.name = name
        self.tcp_port = int(tcp_port)
        self.known = {}            #peers discovered {(ip, port): last_seen_ts}
        self.outgoing = {}         # tcp connections {(ip, port): (reader, writer)}
        self.avg = RollingAvg30s()

    #Discovery udp 
    async def discovery_beacon(self):
        msg = json.dumps({"name": self.name, "tcp_port": self.tcp_port}).encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setblocking(False)
            while True:
                s.sendto(msg, ("255.255.255.255", DISCOVERY_PORT)) #Broadcasting 
                await asyncio.sleep(BEACON_SEC)
    #Listening for upd broadcasts
    async def discovery_listener(self):
        loop = asyncio.get_running_loop()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with suppress(Exception):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(("", DISCOVERY_PORT))
        s.setblocking(False)  # non-blocking + awaited recieving 
        while True:
            data, (ip, _) = await loop.sock_recvfrom(s, 2048)
            try:
                info = json.loads(data.decode())
                if info.get("name") == self.name:
                    continue
                peer_key = (ip, int(info["tcp_port"]))
                self.known[peer_key] = time.time()
            except Exception:
                pass


    #recieves and json lines from peers, updates the rolling averages, and  sends back an acknowlegdement 
    # While also printing the information to the terminal
    async def handle_conn(self, reader, writer):
        addr = writer.get_extra_info("peername")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode())
                    # expecting the schema from sensor.py: {"sensor_id": SID, "density": x}
                    density = float(msg.get("density", 0.0))
                    self.avg.add(density)
                    rolling = self.avg.avg()
                    # mimic server ack
                    ack = {"ok": True, "rolling_avg_30s": rolling}
                    writer.write((json.dumps(ack) + "\n").encode())
                    await writer.drain()
                    print(f"[IN  {addr}] {msg} | avg30={rolling:.2f}")
                except Exception as e:
                    err = {"ok": False, "error": str(e)}
                    writer.write((json.dumps(err) + "\n").encode())
                    await writer.drain()
        finally:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
    #This starts the server up and listening for incoming peer connections 
    async def tcp_server(self):
        server = await asyncio.start_server(self.handle_conn, "0.0.0.0", self.tcp_port)
        print(f"[{self.name}] TCP server on 0.0.0.0:{self.tcp_port}")
        async with server:
            await server.serve_forever()

    
    async def dialer(self):
        while True:
            now = time.time()
            # Removes peers that have expireded  (fault tolerance)
            for k, ts in list(self.known.items()):
                if now - ts > PEER_TTL_SEC:
                    self.known.pop(k, None)
                    conn = self.outgoing.pop(k, None)
                    if conn:
                        _, w = conn
                        w.close()
                        with suppress(Exception):
                            await w.wait_closed()

            # connect to any new peers
            for peer in list(self.known.keys()):
                if peer not in self.outgoing:
                    ip, port = peer
                    # avoid self connection on localhost
                    if ip in ("127.0.0.1", "localhost") and port == self.tcp_port:
                        continue
                    try:
                        r, w = await asyncio.open_connection(ip, port)
                        self.outgoing[peer] = (r, w)
                        print(f"[{self.name}] Connected to {peer}")
                        asyncio.create_task(self.sender_loop(peer, r, w))
                        asyncio.create_task(self.reader_log(peer, r))
                        #This creates both a sender and a reader loop for every connection
                    except Exception:
                        pass

            await asyncio.sleep(1.0)

    # Send sensor style messages periodically (this replaces sensor.py’s loop)
    async def sender_loop(self, peer, reader, writer):
        while not writer.is_closing():
            density = max(0.0, random.gauss(35, 10))
            msg = {"sensor_id": self.name, "density": density}
            try:
                writer.write((json.dumps(msg) + "\n").encode())
                await writer.drain()
            except Exception:
                break
            await asyncio.sleep(0.5)

    # Prints acknowledgements recieved from peers
    async def reader_log(self, peer, reader):
        addr = f"{peer[0]}:{peer[1]}"
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                print(f"[ACK {addr}] {line.decode().strip()}")
        except Exception:
            pass
    #here we're just running all of them together 
    async def run(self):
        await asyncio.gather(
            self.discovery_beacon(),
            self.discovery_listener(),
            self.tcp_server(),
            self.dialer(),
        )

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="unique peer id (e.g., P-001)")
    ap.add_argument("--port", type=int, default=DEFAULT_TCP_PORT, help="TCP listen port")
    args = ap.parse_args()
    asyncio.run(Peer(args.name, args.port).run())
    #Start a peer from the command line using the command 
    #python peer_p2p.py --name p-001 --port 5001

if __name__ == "__main__":
    main()
