import pika # rabbitmq client library
import json
import time

#connection to RabbitMQ, TCP connection to local broker
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

#light weight session over TCP connection
channel = connection.channel()

#declaring an exchange
channel.exchange_declare(exchange='game.events', exchange_type='topic', durable=True)

msg = {
    "type": "match.ready",
    "matchId": "demo-1",
    "timestamp": int(time.time())
 }

#sending publishing to routing key of "game.events" with the message we created
channel.basic_publish(exchange='game.events', routing_key='match.ready', body=json.dumps(msg))
print("Published match.ready")

ended = {
    "type": "match.ended", 
    "matchId": "demo-1",
    "winners": ["p-101"],
    "players": ["p-101", "p-102", "p-103", "p-104"],
    "timestamp": int(time.time())
}

channel.basic_publish(
    exchange="game.events",
    routing_key="match.ended",
    body=json.dumps(ended)
)

print("Published match.ended")
#close connection after everything is done
connection.close()