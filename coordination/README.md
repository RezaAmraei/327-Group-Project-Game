# Milestone 4 - Part 2 (Two-Phase Commit Demo)

## Description
This folder contains a simple Two-Phase Commit (2PC) example.  
We simulate one coordinator and three participants.  
The coordinator asks everyone to vote on the winner.

- If all vote commit → final decision is COMMIT  
- If anyone aborts or times out → final decision is ABORT


## Requirements
- Python 3  
- Terminal

## Files
- `coordination_2pc.py`

## Instructions
To run the demo:

open your terminal and run
python3 coordination_2pc.py
