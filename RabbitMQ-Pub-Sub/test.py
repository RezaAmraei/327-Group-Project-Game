import pika
import json
import time
import random



#rabbit mq connection setup 
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

channel.exchange_declare(
    exchange='game.events',
    exchange_type='topic',
    durable=True
)

#lamport clock 
lamport = 0

def tick():
    global lamport
    lamport += 1
    return lamport


def publish_event(rk, payload):
    #attatching lamport time stamp and publishing the vene 
    ts = tick()
    payload["lamport"] = ts

    channel.basic_publish(
        exchange="game.events",
        routing_key=rk,
        body=json.dumps(payload)
    )

    print(f"[PUBLISH] rk={rk:<15} lamport={ts:<3} payload={payload}")


#event types simulate game behviors 
players = ["p-101", "p-102", "p-103", "p-104"]

events = [
    ("match.ready", {"type": "match.ready", "matchId": "test-1"}),
    ("player.p-101.result", {"type": "player.result", "player": "p-101", "score": 80}),
    ("player.p-102.result", {"type": "player.result", "player": "p-102", "score": 95}),
    ("player.p-103.result", {"type": "player.result", "player": "p-103", "score": 67}),
    ("match.ended", {"type": "match.ended", "matchId": "test-1", "winner": "p-102"}),
]


print("\nstarting the out of order event test\n")

# shuffle events to intentionally break ordering
random.shuffle(events)

for rk, payload in events:

    # makiing the  arrival even more random
    delay = random.uniform(0.1, 1.0)

    publish_event(rk, payload)

    print(f"  -> artificial delay: {delay:.2f} seconds\n")

    time.sleep(delay)

print("We are finished ! ")

connection.close()
