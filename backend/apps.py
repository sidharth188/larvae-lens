import traceback
import uuid
import cv2
import gc
from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_model.classifier import classify_risk
from database.cloudant_config import db
from database.cloudant_config import db, users_db
from notification.whatsaap import send_whatsapp_alert
from flask import send_from_directory
import os

app = Flask(__name__)



CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return "Larvae Lens Backend Running"

# Upload Route
@app.route('/upload', methods=['POST'])
def upload():

    image = request.files['image']
    if image.content_length and image.content_length > 5 * 1024 * 1024:

     return jsonify({

        "message":"Image too large"

    }),400

    latitude = request.form['latitude']

    longitude = request.form['longitude']

    from datetime import datetime

    timestamp = datetime.utcnow().isoformat()
    
    priority = request.form.get('priority')
    email = request.form['email']

    unique_filename = f"{uuid.uuid4()}_{image.filename}"

    image_path = os.path.join(
    UPLOAD_FOLDER,
    unique_filename
)

    image.save(image_path)
    
    img = cv2.imread(image_path)

    img = cv2.resize(img, (600, 600))

    cv2.imwrite(image_path, img)
    image_url = f"https://larvae-lens-backend.onrender.com/uploads/{unique_filename}"
    risk_level = classify_risk(image_path)
    del img
    gc.collect()

    try:

      if True:

        send_whatsapp_alert(

            risk_level,

            latitude,

            longitude,
            image_url

        )

    except Exception as e:

      import traceback

      print("WhatsApp Error:", e)

      traceback.print_exc()


    report_data = {

    "image": unique_filename,
  

    "latitude": latitude,

    "longitude": longitude,

    "timestamp": timestamp,

    "risk_level": risk_level,

    "priority": priority,
    "email": email,

    "status": "PENDING"

    

}

    db.create_document(report_data)

    print("Risk Level:", risk_level)

    print("Image Saved:", unique_filename)

    print("Latitude:", latitude)
    print("Longitude:", longitude)
    print("Timestamp:", timestamp)
    print("UPLOAD SUCCESS")
    return jsonify({
    "message":"Report uploaded successfully",
    "risk_level": risk_level,
    "latitude":latitude,
    "longitude":longitude
   })


@app.route('/reports', methods=['GET'])
def get_reports():

    reports = []

    docs = list(db)

    docs = docs[-30:]

    for doc in docs:

        report = {

            "id": doc.get('_id'),

            "image": doc.get('image'),

            "risk_level": doc.get('risk_level'),

            "status": doc.get('status'),

            "latitude": doc.get('latitude'),

            "longitude": doc.get('longitude'),

            "priority": doc.get('priority'),
            "timestamp": doc.get('timestamp'),

        }

        reports.append(report)

    return jsonify(reports)

@app.route('/update-status/<doc_id>', methods=['PUT'])
def update_status(doc_id):

    doc = db[doc_id]

    doc['status'] = "COMPLETED"

    doc.save()

    return jsonify({
        "message":"Status Updated"
    })

import requests
from flask import redirect

@app.route('/login')
def login():

    authorization_url = (
        "YOUR_AUTHORIZATION_URL"
    )

    return redirect(authorization_url)

@app.route('/callback')
def callback():

    code = request.args.get("code")

    print("Authorization Code:", code)

    return redirect(
        "http://127.0.0.1:5500/dashboard.html"
    )

@app.route('/signup', methods=['POST'])
def signup():

    data = request.json

    name = data['name']
    email = data['email']
    password = data['password']

    # Check existing user
    for user in users_db:

        if user.get('email') == email:

            return jsonify({

                "success": False,

                "message": "Email already exists"

            })

    user_data = {

        "name": name,

        "email": email,

        "password": password

    }

    users_db.create_document(user_data)

    return jsonify({

        "success": True,

        "message":"User Registered Successfully"

    })

@app.route('/login-user', methods=['POST'])
def login_user():

    data = request.json

    email = data['email']

    password = data['password']

    for user in users_db:

        if (

            user.get('email') == email

            and

            user.get('password') == password

        ):

            return jsonify({

                "success": True,

                "message":"Login Successful",
                "name": user.get('name'),
                "email": user.get('email')

            })

    return jsonify({

        "success": False,

        "message":"Invalid Credentials"

    })
@app.route('/user-reports/<email>', methods=['GET'])
def user_reports(email):

    reports = []

    for doc in db:

        if doc.get('email') == email:

            report = {

                "risk_level":
                doc.get('risk_level'),

                "status":
                doc.get('status'),

                "timestamp":
                doc.get('timestamp')

            }

            reports.append(report)

    reports= reports[::-1]  # Reverse to show latest first

    return jsonify(reports)
if __name__ == '__main__':
    app.run(debug=False)