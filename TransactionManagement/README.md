# Transaction Management – Winner Lock System

This folder contains the code for **transaction management and concurrency control** for Milestone 4 (Part 3).

Goal:  
Make sure **only one player** can become the final winner, even if multiple players try to win at almost the same time.

We treat “declaring the winner” as a **transaction**:
- Start a transaction
- Check if a winner already exists
- If not, set this player as the winner
- Commit (or abort if there’s a conflict)

---

## 1. `transactions.py`

This file has the **core transaction logic** and a small local demo.

Main pieces:

- `TransactionStatus` and `Transaction`  
  Store:
  - the transaction id  
  - status (`BEGIN`, `COMMITTED`, `ABORTED`)  
  - staged writes  
  - version snapshots (for conflict checks)

- `TransactionManager`  
  Provides:
  - `begin()` – start a transaction  
  - `read(transaction_id, resource_id)` – read a value in a transaction  
  - `write(transaction_id, resource_id, value)` – stage a change  
  - `commit(transaction_id)` – try to apply changes (may abort on conflict)  
  - `abort(transaction_id)` – cancel and discard changes  
  - `set_resource_initial(resource_id, value)` – set initial value  
  - `get_resource(resource_id)` – read committed value  

  It uses:
  - a lock for thread safety  
  - a version number per resource (optimistic concurrency control)

- `GameState`  
  Wraps `TransactionManager` for our use case:
  - Manages a single shared value: `winner`
  - `get_committed_winner()` → returns the current winner (or `None`)
  - `declare_winner_transactional(player_id)` → tries to declare this player as winner using a transaction

At the bottom of this file is a demo with two threads (`player_A` and `player_B`) racing to become winner.

---

## 2. `winner_coordinator.py`

This file turns the same logic into a simple **network coordinator**.

What it does:

- Starts a TCP server on `127.0.0.1:5001`
- Creates a `GameState` and holds the shared `winner` state
- Accepts simple text commands from clients:

  DECLARE_WINNER <player_id>

- For each command it:
  - calls `game_state.declare_winner_transactional(player_id)`
  - responds with:
    - `WON`  → this player became the official winner  
    - `LOST` → a winner already exists (transaction aborted)

This shows begin/commit/abort working across multiple processes (nodes) via the coordinator.

---

## 3. How to test it

### A. Local demo (single process, threads)

From the `TransactionManagement` folder:

    python3 transactions.py

You should see something like:

    [player_A] attempt finished -> WON
    [player_B] attempt finished -> LOST (transaction aborted)
    Final committed winner: {'player_id': 'player_A', 'timestamp': ...}

(Who wins may swap, but there is always exactly one winner.)

---

### B. Distributed-style demo (multiple processes)

1. Start the coordinator (server)

   From the `TransactionManagement` folder:

       python3 winner_coordinator.py

2. Simulate Node A

   In a second terminal, from the same folder:

       nc 127.0.0.1 5001

   Then type:

       DECLARE_WINNER player_A

3. Simulate Node B

   In a third terminal, from the same folder:

       nc 127.0.0.1 5001

   Then type:

       DECLARE_WINNER player_B

Exactly one node will receive `WON`, and the other will receive `LOST`.  
This demonstrates that, even across multiple processes, **only one winner is ever committed**.