from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from uuid import uuid4
from time import time
from collections import deque
import uvicorn

app = FastAPI()

# model creation
class EnqueueRequest(BaseModel):
    playerId: str = Field(..., min_length=1)

class Ticket(BaseModel):
    id: str
    status: str
    createdAt: int
    matchId: str | None = None

class Match(BaseModel):
    id: str
    players: List[str]

# app setup
TEAM_SIZE = 4 # 4-player multiplayer game
waiting: deque[str] = deque() # queue to store player ids of players waiting to be matched
tickets: dict[str, Ticket] = {} # maps ticket ids to Ticket objects
player_ticket: dict[str, str] = {} # maps player ids to ticket ids

def now_ms() -> int: # timestamp in milliseconds
    return int(time() * 1000)

# matchmaking core
def try_match() -> list[Match]:
    made: list[Match] = []
    if len(waiting) < TEAM_SIZE:
        return made
    
    team = [waiting.popleft() for _ in range(TEAM_SIZE)]
    match = Match(id=f"m-{uuid4().hex[:8]}", players=team)

    # update ticket status
    for pid in team:
        tid = player_ticket[pid]
        t = tickets[tid]
        t.status = "matched"
        t.matchId = match.id
    
    made.append(match)
    return made

# enqueue
@app.post("/enqueue")
def enqueue(body: EnqueueRequest):
    pid = body.playerId
    if pid in player_ticket:
        t = tickets[player_ticket[pid]]
        return {"ticket": t, "matches": []}  # <-- MUST return a dict

    tid = f"t-{uuid4().hex[:8]}"
    t = Ticket(id=tid, status="searching", createdAt=now_ms())
    tickets[tid] = t
    player_ticket[pid] = tid
    waiting.append(pid)

    matches = try_match()
    return {"ticket": t, "matches": matches}

@app.delete("/ticket/{tid}", status_code=204)
def cancel(tid: str):
    t = tickets.get(tid)
    if not t or t.status != "searching":
        raise HTTPException(409, "Cannot cancel (ticket not found or already matched).")

    # find which player owns this ticket
    pid = next((p for p, tt in player_ticket.items() if tt == tid), None)

    # remove from queue if still waiting
    if pid and pid in waiting:
        waiting.remove(pid)
        player_ticket.pop(pid, None)

    # mark ticket as canceled
    t.status = "canceled"
    return

@app.get("/ticket/{tid}", response_model=Ticket)
def get_ticket(tid: str):
    t = tickets.get(tid)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)


