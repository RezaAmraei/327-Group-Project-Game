# reads messages from a named pipe
import os

PIPE = "/tmp/ipc_demo_pipe"

def main():
    if not os.path.exists(PIPE):
        os.mkfifo(PIPE)
    print("[pipe] waiting for writer...")
    with open(PIPE, "r") as f:
        for line in f:
            print("[pipe] <-", line.strip())

if __name__ == "__main__":
    main()

