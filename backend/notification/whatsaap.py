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

    longitude

):

    message = f'''

⚠ Larvae Lens Alert

Risk Level: {risk_level}

Location:
{latitude}, {longitude}

Status: PENDING

Municipality action required.
'''

    client.messages.create(

        body=message,

        from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),

        to=os.getenv("YOUR_WHATSAPP_NUMBER")

    )

    print("WhatsApp Alert Sent")