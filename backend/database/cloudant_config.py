from cloudant.client import Cloudant
from dotenv import load_dotenv
import os

load_dotenv()

client = Cloudant.iam(

    os.getenv("CLOUDANT_USERNAME"),

    os.getenv("CLOUDANT_PASSWORD"),

    connect=True,

    url=os.getenv("CLOUDANT_URL")

)

database_name = "larvae_reports"

if database_name in client.all_dbs():

    db = client[database_name]

else:

    db = client.create_database(database_name)

users_database = "users"

if users_database in client.all_dbs():

    users_db = client[users_database]

else:

    users_db = client.create_database(users_database)
    
print("Cloudant Connected Successfully")