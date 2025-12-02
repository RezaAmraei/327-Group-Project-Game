import pika # rabbitmq client library
import json
import time

#connection to RabbitMQ, TCP connection to local broker
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

#light weight session over TCP connection
channel = connection.channel()

#declaring an exchange
channel.exchange_declare(exchange='game.events', exchange_type='topic', durable=True)
lamport = 0
def tick():
    global lamport
    lamport+=1
    return lamport


def publish_event(routing_key,payload):
    lamport_ts = tick()
    payload["lamport"] = lamport_ts
    
    channel.basic_publish(exchange='game.events',routing_key=routing_key,body=json.dumps(payload))
    print(f"[PUBLISH] rk='{routing_key}' lamport={lamport_ts} body={payload}")
msg = {
    "type": "match.ready",
    "matchId": "demo-1",
    "timestamp": int(time.time())
 }

#sending publishing to routing key of "game.events" with the message we created
publish_event("match.ready", msg)


ended = {
    "type": "match.ended", 
    "matchId": "demo-1",
    "winners": ["p-101"],
    "players": ["p-101", "p-102", "p-103", "p-104"],
    "timestamp": int(time.time())
}

publish_event("match.ended", ended)
print("Published match.ended")
#close connection after everything is done
connection.close()