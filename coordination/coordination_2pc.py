import threading
import queue
import time

# participant runs in its own thread and talks to the coordinator
class Participant(threading.Thread):
    def __init__(self, name, inbox, coord_outbox, behavior="commit"):
        super().__init__(daemon=True)
        self.name = name
        self.inbox = inbox          # messages from coordinator
        self.coord_outbox = coord_outbox  # messages to coordinator
        self.behavior = behavior    # "commit", "abort", or "timeout"

    def run(self):
        while True:
            msg = self.inbox.get()
            mtype = msg.get("type")

            if mtype == "PREPARE":
                winner = msg.get("winner")
                print(f"{self.name} got PREPARE for {winner}")

                if self.behavior == "timeout":
                    # simulate slow or dead node
                    print(f"{self.name} is timing out (no vote)")
                    continue

                # decide which vote to send back
                if self.behavior == "abort":
                    vote = "VOTE_ABORT"
                else:
                    vote = "VOTE_COMMIT"

                print(f"{self.name} sends {vote}")
                self.coord_outbox.put({"from": self.name, "type": vote})

            elif mtype in ("COMMIT", "ABORT"):
                # final result from coordinator
                print(f"{self.name} final result = {mtype}")
                break

            self.inbox.task_done()


# coordinator sends prepare, collects votes, and decides commit or abort
class Coordinator:
    def __init__(self, participants, inbox, timeout=2.0):
        self.participants = participants    # list of (name, queue)
        self.inbox = inbox                  # votes from participants
        self.timeout = timeout              # max wait time for votes

    def run_2pc(self, winner):
        print("")
        print("PREPARE PHASE")
        print("coordinator asks everyone to vote")

        # send prepare to all participants
        for name, inbox in self.participants:
            inbox.put({"type": "PREPARE", "winner": winner})

        votes = {}
        start = time.time()

        # collect votes until all are in or timeout happens
        while len(votes) < len(self.participants):
            left = self.timeout - (time.time() - start)
            if left <= 0:
                print("coordinator timed out waiting for votes")
                break

            try:
                msg = self.inbox.get(timeout=left)
            except queue.Empty:
                print("no more votes received")
                break

            sender = msg.get("from")
            vtype = msg.get("type")
            if sender and vtype in ("VOTE_COMMIT", "VOTE_ABORT"):
                print(f"coordinator got {vtype} from {sender}")
                votes[sender] = vtype
                self.inbox.task_done()

        # decide global result
        if len(votes) == len(self.participants) and all(v == "VOTE_COMMIT" for v in votes.values()):
            decision = "COMMIT"
        else:
            decision = "ABORT"

        print("")
        print("DECISION PHASE")
        print(f"coordinator decides: {decision}")

        # send final result to everyone
        for name, inbox in self.participants:
            inbox.put({"type": decision})

        return decision


# first test: everyone votes commit
def scenario_all_commit():
    print("")
    print("=== SCENARIO 1: everyone commits ===")

    coord_inbox = queue.Queue()
    p1_in = queue.Queue()
    p2_in = queue.Queue()
    lb_in = queue.Queue()

    # all participants behave and vote commit
    p1 = Participant("Player1", p1_in, coord_inbox, behavior="commit")
    p2 = Participant("Player2", p2_in, coord_inbox, behavior="commit")
    lb = Participant("Leaderboard", lb_in, coord_inbox, behavior="commit")

    p1.start()
    p2.start()
    lb.start()

    parts = [("Player1", p1_in), ("Player2", p2_in), ("Leaderboard", lb_in)]
    coord = Coordinator(parts, coord_inbox)
    result = coord.run_2pc("Player1")

    time.sleep(0.3)
    return result


# second test: one abort and one timeout
def scenario_abort():
    print("")
    print("=== SCENARIO 2: an abort and a timeout ===")

    coord_inbox = queue.Queue()
    p1_in = queue.Queue()
    p2_in = queue.Queue()
    lb_in = queue.Queue()

    # player1 commits, player2 aborts, leaderboard times out
    p1 = Participant("Player1", p1_in, coord_inbox, behavior="commit")
    p2 = Participant("Player2", p2_in, coord_inbox, behavior="abort")
    lb = Participant("Leaderboard", lb_in, coord_inbox, behavior="timeout")

    p1.start()
    p2.start()
    lb.start()

    parts = [("Player1", p1_in), ("Player2", p2_in), ("Leaderboard", lb_in)]
    coord = Coordinator(parts, coord_inbox)
    result = coord.run_2pc("Player1")

    time.sleep(0.3)
    return result


def main():
    r1 = scenario_all_commit()
    r2 = scenario_abort()

    print("")
    print("Summary:")
    print("Scenario 1:", r1)
    print("Scenario 2:", r2)


if __name__ == "__main__":
    main()
