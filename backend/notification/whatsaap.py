from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client(

    os.getenv("TWILIO_ACCOUNT_SID"),

    os.getenv("TWILIO_AUTH_TOKEN")

)

def send_whatsapp_alert(

    risk_level,

    latitude,

    longitude,

    image_url

):

    try:

        message = f'''

⚠ Larvae Lens Alert

Risk Level: {risk_level}

Location:
{latitude}, {longitude}

Status: PENDING

Image: {image_url}

Municipality action required.
'''

        msg = client.messages.create(

            body=message,

            from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),

            to=os.getenv("YOUR_WHATSAPP_NUMBER")

        )

        print("WhatsApp Alert Sent")
        print("SID:", msg.sid)
        print("MESSAGE STATUS:", msg.status)

    except Exception as e:

        print("TWILIO ERROR:", e)