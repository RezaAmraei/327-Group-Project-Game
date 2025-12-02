import pika
import json

#connection to RabbitMQ, TCP connection to local broker
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

#light weight session over TCP connection
channel = connection.channel()

#
def on_msg(ch, method, props, body):
    try:
        print("notify:", method.routing_key, json.loads(body))
    except Exception:
        print("notify:", method.routing_key, body.decode())
    #lets rabbitMQ know the messaged was processed and it can be removed from queue
    ch.basic_ack(method.delivery_tag)
    
channel.basic_qos(prefetch_count=10)
channel.basic_consume(queue="notify-gateway", on_message_callback=on_msg, auto_ack=False)

#enters a loop that waits for messages and invoking the callback eaach time
print("listening on notify-gateway... (Crtl+C to stop this)")
channel.start_consuming()