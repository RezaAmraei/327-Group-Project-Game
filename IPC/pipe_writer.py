# writes messages into a named pipe
import os, sys, time

PIPE = "/tmp/ipc_demo_pipe"

def main():
    if not os.path.exists(PIPE):
        print("[pipe] pipe missing, start reader first")
        sys.exit(1)
    with open(PIPE, "w") as f:
        for i in range(10):
            f.write(f"msg {i}\n")
            f.flush()
            print("[pipe] -> msg", i)
            time.sleep(0.3)

if __name__ == "__main__":
    main()

