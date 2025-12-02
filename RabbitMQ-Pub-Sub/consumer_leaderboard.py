import pika
import json

#connection to RabbitMQ, TCP connection to local broker
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

#light weight session over TCP connection
channel = connection.channel()

def on_msg(ch, method, props, body):
    event = json.loads(body.decode('utf-8'))
    print("leaderboard:", method.routing_key, event)
    ch.basic_ack(method.delivery_tag)
    
channel.basic_qos(prefetch_count=10)
channel.basic_consume(queue="leaderboard-worker", on_message_callback=on_msg, auto_ack=False)

print("listening on leaderboard-worker ... (Crtl + C to stop this)")
channel.start_consuming()