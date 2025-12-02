"""
OS-Level Concurrency demo for the Milestone 3 write-up

This module shows a node that uses Python threads + synchronization primitives
(Lock, Semaphore, Queue, Event) to process concurrent work safely.

It can run stand-alone to demonstrate:
 - Producer/consumer with backpressure via bounded queues
 - State protection with Lock (and a --no-locks flag to show races)
 - Capacity control with Semaphore (e.g., player slots)
 - Event signaling for notable conditions (e.g., accident/low-health)

Usage examples:
    python os_concurrency_node.py --duration 15
    python os_concurrency_node.py --duration 15 --producers 4 --max-players 4
    python os_concurrency_node.py --duration 15 --no-locks  # intentionally race

The code is written to be easy to stitch into the existing P2P peer by
replacing the RandomProducer with a network receiver that enqueues
arriving messages, and replacing Outbox with a network sender.
"""

from __future__ import annotations
import argparse
import json
import queue
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# message types and schemas

@dataclass
class Msg:
    kind: str  # 'join' | 'leave' | 'update' | 'ping'
    player_id: str
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "kind": self.kind,
            "player_id": self.player_id,
            "payload": self.payload,
            "ts": self.ts,
        })

# shared state & sync primitives

@dataclass
class SharedState:
    # game-like state to show contention
    player_health: Dict[str, int] = field(default_factory=dict)
    player_order: List[str] = field(default_factory=list)

    # stats/metrics
    messages_processed: int = 0
    joins: int = 0
    leaves: int = 0
    updates: int = 0

    # synchronization
    lock: Optional[threading.Lock] = None  # injected; None means intentionally unsafe

    def with_lock(self):
        # context manager that becomes a no-op when lock is None
        class _Guard:
            def __init__(self, lock: Optional[threading.Lock]):
                self._lock = lock
            def __enter__(self):
                if self._lock:
                    self._lock.acquire()
            def __exit__(self, exc_type, exc, tb):
                if self._lock:
                    self._lock.release()
        return _Guard(self.lock)

# worker threads

class RandomProducer(threading.Thread):
    # simulates inbound network traffic by producing random messages
    def __init__(self, name: str, out_q: queue.Queue, shutdown: threading.Event, rate_hz: float = 20.0):
        super().__init__(name=name, daemon=True)
        self.out_q = out_q
        self.shutdown = shutdown
        self.period = 1.0 / max(rate_hz, 0.1)
        self.players = [f"P{i:03d}" for i in range(1, 32)]

    def run(self):
        while not self.shutdown.is_set():
            kind = random.choices(["join", "update", "leave"], weights=[0.1, 0.8, 0.1])[0]
            pid = random.choice(self.players)
            if kind == "update":
                payload = {"delta": random.randint(-7, 5)}  # negative means damage
            else:
                payload = {}
            msg = Msg(kind=kind, player_id=pid, payload=payload)
            try:
                self.out_q.put(msg, timeout=0.2)
            except queue.Full:
                # backpressure: drop on full to simulate UDP-like behavior
                pass
            time.sleep(self.period * random.uniform(0.5, 1.5))

class SimulationWorker(threading.Thread):
    # consumes inbound messages and mutates SharedState safely (or not)
    def __init__(self, name: str, in_q: queue.Queue, out_q: queue.Queue, state: SharedState,
                 slots: threading.Semaphore, low_health_event: threading.Event, shutdown: threading.Event,
                 min_health: int = 0, max_health: int = 100):
        super().__init__(name=name, daemon=True)
        self.in_q = in_q
        self.out_q = out_q
        self.state = state
        self.slots = slots
        self.low_health_event = low_health_event
        self.shutdown = shutdown
        self.min_health = min_health
        self.max_health = max_health

    def run(self):
        while not self.shutdown.is_set():
            try:
                msg: Msg = self.in_q.get(timeout=0.2)
            except queue.Empty:
                continue

            if msg.kind == "join":
                # attempt to acquire a slot (capacity control)
                acquired = self.slots.acquire(blocking=False)
                with self.state.with_lock():
                    if acquired:
                        if msg.player_id not in self.state.player_health:
                            self.state.player_health[msg.player_id] = self.max_health
                            self.state.player_order.append(msg.player_id)
                            self.state.joins += 1
                            self._emit_ack("join.ok", msg)
                        else:
                            # already present: release the acquired slot and ignore
                            self.slots.release()
                            self._emit_ack("join.dup", msg)
                    else:
                        # capacity full
                        self._emit_ack("join.full", msg)

            elif msg.kind == "leave":
                # release a slot if the player existed
                existed = False
                with self.state.with_lock():
                    if msg.player_id in self.state.player_health:
                        existed = True
                        self.state.player_health.pop(msg.player_id, None)
                        try:
                            self.state.player_order.remove(msg.player_id)
                        except ValueError:
                            pass
                        self.state.leaves += 1
                        self._emit_ack("leave.ok", msg)
                    else:
                        self._emit_ack("leave.missing", msg)
                if existed:
                    self.slots.release()

            elif msg.kind == "update":
                with self.state.with_lock():
                    if msg.player_id in self.state.player_health:
                        h = self.state.player_health[msg.player_id]
                        h = max(self.min_health, min(self.max_health, h + int(msg.payload.get("delta", 0))))
                        self.state.player_health[msg.player_id] = h
                        self.state.updates += 1
                        if h <= 20:  # signal an event when health is low
                            self.low_health_event.set()
                        self._emit_ack("update.ok", msg)
                    else:
                        # allow update to trigger implicit join (intentionally racy without locks)
                        self.state.player_health[msg.player_id] = self.max_health
                        self.state.player_order.append(msg.player_id)
                        self.state.joins += 1
                        self._emit_ack("update.imp_join", msg)

            else:
                self._emit_ack("noop", msg)

            self.state.messages_processed += 1
            self.in_q.task_done()

    def _emit_ack(self, kind: str, src: Msg):
        ack = Msg(kind=kind, player_id=src.player_id, payload={"src": src.kind, "t": time.time()})
        try:
            self.out_q.put_nowait(ack)
        except queue.Full:
            # drop acks when outbox is congested
            pass

class OutboxWorker(threading.Thread):
    # consumes outbound messages and 'sends' them (here we just log)
    def __init__(self, name: str, out_q: queue.Queue, shutdown: threading.Event):
        super().__init__(name=name, daemon=True)
        self.out_q = out_q
        self.shutdown = shutdown

    def run(self):
        while not self.shutdown.is_set():
            try:
                msg: Msg = self.out_q.get(timeout=0.2)
            except queue.Empty:
                continue
            # replace this print with real network send in P2P integration
            print(f"[OUTBOX] {msg.kind} -> {msg.player_id}")
            self.out_q.task_done()

class LoggerWorker(threading.Thread):
    # periodically prints a snapshot and checks invariants to reveal races
    def __init__(self, name: str, state: SharedState, slots: threading.Semaphore,
                 inbound: queue.Queue, outbound: queue.Queue,
                 low_health_event: threading.Event, shutdown: threading.Event, interval: float = 1.0):
        super().__init__(name=name, daemon=True)
        self.state = state
        self.slots = slots
        self.inbound = inbound
        self.outbound = outbound
        self.low_health_event = low_health_event
        self.shutdown = shutdown
        self.interval = interval

    def run(self):
        while not self.shutdown.is_set():
            time.sleep(self.interval)
            # use the lock if available for a consistent snapshot
            with self.state.with_lock():
                active = len(self.state.player_health)
                # WARNING: semaphore._value is CPython-specific; we derive capacity via a try-acquire
                free_slots = self._peek_free_slots()
                msgs = self.state.messages_processed
                joins, leaves, updates = self.state.joins, self.state.leaves, self.state.updates
                q_in, q_out = self.inbound.qsize(), self.outbound.qsize()

                invariants_ok = (active >= 0)
                # optional stronger invariant if locks enabled: order list matches keys count
                if self.state.lock is not None:
                    invariants_ok = invariants_ok and (active == len(self.state.player_order))

                print(
                    f"[STATS] active={active} free_slots≈{free_slots} "
                    f"msgs={msgs} j/l/u={joins}/{leaves}/{updates} q(in/out)={q_in}/{q_out} "
                    f"invariants_ok={invariants_ok}"
                )

                if self.low_health_event.is_set():
                    # consume the event and log it
                    self.low_health_event.clear()
                    low = [p for p, h in self.state.player_health.items() if h <= 20]
                    print(f"[EVENT] low-health players: {low[:5]}{'...' if len(low)>5 else ''}")

    def _peek_free_slots(self) -> int:
        # probe the semaphore to approximate free slots non-destructively
        acquired = self.slots.acquire(blocking=False)
        if acquired:
            self.slots.release()
            return 1  # at least one
        return 0

# driver

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=20, help="seconds to run the demo")
    ap.add_argument("--producers", type=int, default=2, help="number of message producer threads")
    ap.add_argument("--inbound-q", type=int, default=256, help="inbound queue max size")
    ap.add_argument("--outbound-q", type=int, default=256, help="outbound queue max size")
    ap.add_argument("--max-players", type=int, default=8, help="semaphore capacity for player slots")
    ap.add_argument("--no-locks", action="store_true", help="disable locks to demonstrate race conditions")
    args = ap.parse_args()

    shutdown = threading.Event()
    low_health_event = threading.Event()

    inbound_q: queue.Queue = queue.Queue(maxsize=args.inbound_q)
    outbound_q: queue.Queue = queue.Queue(maxsize=args.outbound_q)

    lock = None if args.no_locks else threading.Lock()
    state = SharedState(lock=lock)
    slots = threading.Semaphore(args.max_players)

    # start producers
    producers: List[threading.Thread] = [
        RandomProducer(name=f"producer-{i}", out_q=inbound_q, shutdown=shutdown, rate_hz=25.0)
        for i in range(args.producers)
    ]

    # start workers
    sim = SimulationWorker(
        name="simulation",
        in_q=inbound_q,
        out_q=outbound_q,
        state=state,
        slots=slots,
        low_health_event=low_health_event,
        shutdown=shutdown,
    )
    outbox = OutboxWorker(name="outbox", out_q=outbound_q, shutdown=shutdown)
    logger = LoggerWorker(
        name="logger",
        state=state,
        slots=slots,
        inbound=inbound_q,
        outbound=outbound_q,
        low_health_event=low_health_event,
        shutdown=shutdown,
        interval=1.0,
    )

    threads = producers + [sim, outbox, logger]
    for t in threads:
        t.start()

    # run for the requested duration
    try:
        time.sleep(max(1, args.duration))
    except KeyboardInterrupt:
        pass
    finally:
        shutdown.set()
        # drain queues quickly to let workers exit
        deadline = time.time() + 3
        while time.time() < deadline and (not inbound_q.empty() or not outbound_q.empty()):
            time.sleep(0.05)

    for t in [*producers, sim, outbox, logger]:
        t.join(timeout=1.5)

    # final summary
    print("\n[Summary]")
    print(json.dumps({
        "messages_processed": state.messages_processed,
        "joins": state.joins,
        "leaves": state.leaves,
        "updates": state.updates,
        "active_players": len(state.player_health),
        "no_locks": bool(args.no_locks),
    }, indent=2))


if __name__ == "__main__":
    main()
