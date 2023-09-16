import asyncio
import discord
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
from django.core.mail import send_mail
from django.conf import settings as conf_settings 
from celery import shared_task
from confluent_kafka import Consumer, TopicPartition
import msgpack 
import threading

class ALERT_EMAIL:
    def __init__(self, email, alert,country):
        self.email = email
        self.alert = alert
        self.country = country

    @property
    def PLAIN(self):
        return f'''
        There is a new alert for {self.country}:
        {self.alert}
        '''
    
    @property
    def HTML(self):
        return '''HTML VERSION'''


def slack_message(channel_id, message):
    client = WebClient(token=conf_settings.SLACK_APP_TOKEN)

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e}")

def discord_message(channel_id, message):
    intents = discord.Intents.default()

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print('Logged in as {0.user}'.format(client))
        channel = client.get_channel(channel_id)
        await channel.send(message)
        await client.close()

    client.run(conf_settings.DISCORD_BOT_TOKEN)

def email_message(email, alert, country):
    def send_email():
        alert_email = ALERT_EMAIL(email, alert, country)
        print("email", email)
        send_mail(
            'New Alert',
            alert_email.PLAIN,
            conf_settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

    thread = threading.Thread(target=send_email)
    thread.start()
# email_message("mohhamedfathyy@gmail.com", "test", "Egypt")


@shared_task()
def kafka_alert():
    from ihr.models import IHRUser_notification,IHRUser_Channel

    conf = {
            'bootstrap.servers': "kafka1:29092",
            'group.id': 'alert',
            'default.topic.config': {'auto.offset.reset': 'smallest'}
        }
    
    consumer = Consumer(conf)
    partition = TopicPartition("ihr_raclette_diffrtt_anomalies", 0)
    consumer.assign([partition])
    while True:
        msg = consumer.poll(1.0)
        
        if msg is None:
            print("no msg")
            break
        
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        
        try:
            value = msgpack.unpackb(msg.value())
        except:
            print("value ", msg.value() )
            continue
        value = msgpack.unpackb(msg.value())
        
        # get startpoint and endpoint
        startPoint = value['value']['datapoint']['startpoint']
        endPoint = value['value']['datapoint']['endpoint']
        
        # remove AS,CT,IX from startpoint and endpoint
        startPoint = startPoint[2:]
        endPoint = endPoint[2:]

        # remove v4 or v6 from startpoint and endpoint
        startPoint = startPoint[:-2]
        endPoint = endPoint[:-2]

        # check deviation value
        deviation = value['value']['deviation']

        # deviation 
        # Low: 20 to 30
        # Medium: 31 to 50
        # High: over 50 

        # check users that listen to this route
        # send alert to them

        if deviation > 20:
            channel_users = IHRUser_Channel.objects.filter(channel = startPoint)
            print(channel_users)
            print(len(channel_users))
            for channel in channel_users:
                print("channel ", channel)
                print("frequency ", channel.frequency)
                notified_user = IHRUser_notification.objects.filter(email = channel.name).first()
                print(notified_user)
                if notified_user:
                    
                    if not ((deviation >= 20 and deviation <= 30 and channel.frequency == "normal") or \
                    (deviation >= 31 and deviation <= 50 and channel.frequency == "medium") or \
                    (deviation > 50 and channel.frequency == "high")):
                        continue
                    alert = f"there is a deviation in RTT between {startPoint} and {endPoint}"
                    print("notified_user ", notified_user)
                    if notified_user.email_notification:
                        try:
                            email_message(channel.name, alert,startPoint)
                        except:
                            print("error in email notification")
                    if notified_user.slack_notification_id:
                        slack_message(notified_user.slack_notification_id, alert)
                    if notified_user.discord_notification_id:
                        discord_message(int(notified_user.discord_notification_id), alert)


    consumer.close()
    return True