import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# We need a service account key to use firebase-admin.
# If running on GCP (Cloud Run) with a default service account, 
# firebase_admin.initialize_app() can be called without creds.
# But for local dev, we might need a JSON key path.

def initialize_firestore():
    # If a custom service account key JSON is provided as a string in the environment
    service_account_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    if service_account_json_str:
        try:
            cert_dict = json.loads(service_account_json_str)
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print("Error parsing FIREBASE_SERVICE_ACCOUNT_JSON:", e)
            firebase_admin.initialize_app()
    else:
        # Default initialization (relies on GOOGLE_APPLICATION_CREDENTIALS or GCP metadata server)
        # This will work automatically on Cloud Run if the service account has Firestore permissions
        try:
            firebase_admin.initialize_app()
        except ValueError:
            # App already initialized
            pass
            
    return firestore.client()

db = initialize_firestore()
print("Firestore Connected Successfully")
