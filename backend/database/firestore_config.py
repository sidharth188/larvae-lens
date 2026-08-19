import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# FIRESTORE INITIALIZATION
#
# Explicitly targets the named database "larvae-lens" instead
# of the default "(default)" database, which is the root
# cause of the 500 Internal Server Errors when saving reports.
#
# On Cloud Run: uses the built-in GCP service account
#               (no JSON key needed — IAM handles auth).
# Local dev:    reads FIREBASE_SERVICE_ACCOUNT_JSON from .env.
# ============================================================

DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID", "larvae-lens")


def initialize_firestore():

    # If the app is already initialised (e.g. hot-reload), skip.
    if not firebase_admin._apps:

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
            # Cloud Run: relies on GCP metadata server / GOOGLE_APPLICATION_CREDENTIALS
            firebase_admin.initialize_app()

    # Pass the named database ID so we connect to "larvae-lens"
    # instead of the "(default)" database that doesn't exist.
    return firestore.client(database_id=DATABASE_ID)


db = initialize_firestore()
print(f"Firestore Connected Successfully → database: {DATABASE_ID}")
