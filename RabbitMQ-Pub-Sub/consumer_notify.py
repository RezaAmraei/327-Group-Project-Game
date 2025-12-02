import pika
import json

#connection to RabbitMQ, TCP connection to local broker
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
lamport = 0
event_buffer = []
#light weight session over TCP connection
channel = connection.channel()

def update_lamport(received_ts):
    global lamport
    lamport = max(lamport, received_ts) +1
    return lamport
def print_order():
    if not event_buffer:
        return
    ordered = sorted(event_buffer, key=lambda e: e["lamport"])
    
    
    print("\nLogial Event Order\n")
    for ev in ordered:
        print(f"event='{ev['type']}', lamport={ev['lamport']}, rk={ev['routing_key']}")

        
        
def on_msg(ch, method, props, body):
    global lamport

    # Convert the incoming body to JSON
    try:
        msg = json.loads(body)
    except:
        msg = {"raw": body.decode()}

    # extract the incoming timestamp (default 0 if missing)
    incoming_ts = msg.get("lamport", 0)

    # update our logical clock
    new_lamport = update_lamport(incoming_ts)

    # add source information just for insights 
    msg["consumer_clock"] = new_lamport
    msg["routing_key"] = method.routing_key

    # store the event for ordering analysis
    event_buffer.append(msg)

    # print raw arrival
    print(f"[ARRIVAL] rk='{method.routing_key}' msg={msg}")

    # print sorted logical order of all received events
    print_order()

    # acknowledge the message so RabbitMQ can delete it
    ch.basic_ack(method.delivery_tag)
    
channel.basic_qos(prefetch_count=10)
channel.basic_consume(queue="notify-gateway",on_message_callback=on_msg,auto_ack=False)

print("listening on notify gateway")
channel.start_consuming()