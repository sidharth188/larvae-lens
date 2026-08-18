import traceback
import uuid
import cv2
import gc
from datetime import datetime
import os

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import firebase_admin

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

from ai_model.classifier import analyze_image
from database.firestore_config import db
from notification.whatsaap import send_whatsapp_alert

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/")
def home():
    return "Larvae Lens Backend Running"


@app.route("/upload", methods=["POST"])
def upload():
    image = request.files["image"]

    if image.content_length and image.content_length > 5 * 1024 * 1024:
        return jsonify({"message": "Image too large"}), 400

    latitude = request.form["latitude"]
    longitude = request.form["longitude"]
    timestamp = datetime.utcnow().isoformat()
    priority = request.form.get("priority")
    email = request.form["email"]
    user_name = request.form["user_name"]

    unique_filename = f"{uuid.uuid4()}_{image.filename}"
    image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    image.save(image_path)

    # Preserve the existing 300x300 processing behavior.
    img = cv2.imread(image_path)
    if img is None:
        return jsonify({"message": "Invalid image"}), 400

    img = cv2.resize(img, (300, 300))
    cv2.imwrite(image_path, img)
    del img
    gc.collect()

    # Competition-v2 now exposes both the original categorical result and
    # interpretable visual evidence/risk score.
    analysis = analyze_image(image_path)
    risk_level = analysis["risk_level"]

    try:
        upload_result = cloudinary.uploader.upload(image_path, folder="larvae_lens")
        image_url = upload_result.get("secure_url")
    except Exception as e:
        print("Cloudinary Error:", e)
        # Fallback to local url if upload fails or just fail the request
        return jsonify({"message": "Failed to upload image to cloud"}), 500
    finally:
        # Clean up local temporary file
        if os.path.exists(image_path):
            os.remove(image_path)

    try:
        send_whatsapp_alert(
            user_name,
            risk_level,
            latitude,
            longitude,
            image_url,
        )
    except Exception as e:
        print("WhatsApp Error:", e)
        traceback.print_exc()

    report_data = {
        "image": unique_filename,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "risk_level": risk_level,
        "risk_score": analysis["risk_score"],
        "analysis_method": analysis["analysis_method"],
        "model_version": analysis["model_version"],
        "evidence": analysis["evidence"],
        "visual_metrics": analysis["metrics"],
        "priority": priority,
        "email": email,
        "status": "PENDING",
    }

    db.collection('larvae_reports').add(report_data)

    print("Risk Level:", risk_level)
    print("Risk Score:", analysis["risk_score"])
    print("Image Saved:", unique_filename)
    print("Latitude:", latitude)
    print("Longitude:", longitude)
    print("Timestamp:", timestamp)
    print("UPLOAD SUCCESS")

    return jsonify({
        "message": "Report uploaded successfully",
        "risk_level": risk_level,
        "risk_score": analysis["risk_score"],
        "evidence": analysis["evidence"],
        "analysis_method": analysis["analysis_method"],
        "model_version": analysis["model_version"],
        "latitude": latitude,
        "longitude": longitude,
    })


@app.route("/reports", methods=["GET"])
def get_reports():
    reports = []

    docs = db.collection('larvae_reports').stream()
    for doc_ref in docs:
        doc = doc_ref.to_dict()
        reports.append({
            "id": doc_ref.id,
            "image": doc.get("image"),
            "risk_level": doc.get("risk_level"),
            "risk_score": doc.get("risk_score"),
            "analysis_method": doc.get("analysis_method"),
            "model_version": doc.get("model_version"),
            "evidence": doc.get("evidence", []),
            "status": doc.get("status"),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
            "priority": doc.get("priority"),
            "timestamp": doc.get("timestamp"),
        })

    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(reports)


@app.route("/update-status/<doc_id>", methods=["PUT"])
def update_status(doc_id):
    db.collection('larvae_reports').document(doc_id).update({"status": "COMPLETED"})
    return jsonify({"message": "Status Updated"})


@app.route("/login")
def login():
    authorization_url = "YOUR_AUTHORIZATION_URL"
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    print("Authorization Code:", code)
    return redirect("http://127.0.0.1:5500/dashboard.html")


@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    name = data["name"]
    email = data["email"]
    password = data["password"]

    existing_users = list(db.collection('users').where(filter=firebase_admin.firestore.FieldFilter("email", "==", email)).stream())
    
    if len(existing_users) > 0:
        return jsonify({
            "success": False,
            "message": "Email already exists",
        })

    db.collection('users').add({
        "name": name,
        "email": email,
        "password": password,
    })

    return jsonify({
        "success": True,
        "message": "User Registered Successfully",
    })


@app.route("/login-user", methods=["POST"])
def login_user():
    data = request.json
    email = data["email"]
    password = data["password"]

    users_ref = db.collection('users').where(filter=firebase_admin.firestore.FieldFilter("email", "==", email)).where(filter=firebase_admin.firestore.FieldFilter("password", "==", password)).stream()
    users_list = list(users_ref)

    if len(users_list) > 0:
        user = users_list[0].to_dict()
        return jsonify({
            "success": True,
            "message": "Login Successful",
            "name": user.get("name"),
            "email": user.get("email"),
        })

    return jsonify({
        "success": False,
        "message": "Invalid Credentials",
    })


@app.route("/user-reports/<email>", methods=["GET"])
def user_reports(email):
    reports = []

    docs = db.collection('larvae_reports').where(filter=firebase_admin.firestore.FieldFilter("email", "==", email)).stream()

    for doc_ref in docs:
        doc = doc_ref.to_dict()
        reports.append({
            "risk_level": doc.get("risk_level"),
            "risk_score": doc.get("risk_score"),
            "evidence": doc.get("evidence", []),
            "status": doc.get("status"),
            "timestamp": doc.get("timestamp"),
        })

    reports.reverse()
    return jsonify(reports)


if __name__ == "__main__":
    app.run(debug=False)
