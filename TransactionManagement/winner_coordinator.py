import socket
from transactions import GameState

HOST = "127.0.0.1"   # localhost for now
PORT = 5001          # pick any free port

def main():
    game_state = GameState()
    print(f"[COORDINATOR] Starting winner service on {HOST}:{PORT}")

    # basic TCP server skeleton
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()

        print("[COORDINATOR] Waiting for connections...")

        while True:
            conn, addr = server_sock.accept()
            print(f"[COORDINATOR] Connection from {addr}")
            handle_client(conn, game_state)


def handle_client(conn, game_state: GameState):
    with conn:
        data = conn.recv(1024)
        if not data:
            return

        message = data.decode().strip()
        print(f"[COORDINATOR] Received: {message}")

        parts = message.split()
        if len(parts) == 2 and parts[0] == "DECLARE_WINNER":
            player_id = parts[1]
            # use your transactional winner logic
            success = game_state.declare_winner_transactional(player_id)
            if success:
                response = "WON\n"
            else:
                response = "LOST\n"
        else:
            response = "ERROR Unknown command\n"

        conn.sendall(response.encode("utf-8"))

if __name__ == "__main__":
    main()