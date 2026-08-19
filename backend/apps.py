import traceback
import uuid
import cv2
import gc
from datetime import datetime
import os

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import cloudinary
import cloudinary.uploader
import firebase_admin
from google.cloud.exceptions import NotFound
from google.cloud.firestore_v1 import Query

load_dotenv()


# ============================================================
# CLOUDINARY
# ============================================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


# ============================================================
# LARVAELENS IMPORTS
# ============================================================

from ai_model.vision_engine import VisionEngine
from database.firestore_config import db
from notification.whatsaap import send_whatsapp_alert


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

vision_engine = VisionEngine()

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# SERVE UPLOADED FILES
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return "Larvae Lens Backend Running"


# ============================================================
# UPLOAD ROUTE
# ============================================================

@app.route("/upload", methods=["POST"])
def upload():
    """
    Primary pipeline:
      1. Accept image + form metadata.
      2. Validate image is readable.
      3. Run V1 Vision Engine (with graceful fallback on failure).
      4. Upload image to Cloudinary.
      5. Send WhatsApp alert.
      6. Save full report to Firestore.
      7. Return flat JSON for frontend compatibility.

    The entire processing block is wrapped in a single
    try/except/finally so that:
      - Any unexpected exception returns a clean JSON 500.
      - The temp image file is always cleaned up.
    """

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image = request.files.get("image")

    if image is None:

        return jsonify({
            "success": False,
            "message": "No image provided"
        }), 400

    if (
        image.content_length
        and image.content_length > 5 * 1024 * 1024
    ):

        return jsonify({
            "success": False,
            "message": "Image too large (max 5 MB)"
        }), 400

    # --------------------------------------------------------
    # FORM FIELDS
    # --------------------------------------------------------

    latitude_raw  = request.form.get("latitude")
    longitude_raw = request.form.get("longitude")
    timestamp     = datetime.utcnow().isoformat()
    priority      = request.form.get("priority", "false")
    email         = request.form.get("email", "")
    user_name     = request.form.get("user_name", "")

    # --------------------------------------------------------
    # SAVE TEMP FILE
    # --------------------------------------------------------

    unique_filename = f"{uuid.uuid4()}_{image.filename or 'image.jpg'}"
    image_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    image.save(image_path)

    # --------------------------------------------------------
    # All further processing inside a single try block so
    # that any unexpected crash still returns clean JSON and
    # the temp file is always deleted in `finally`.
    # --------------------------------------------------------

    image_url = None

    try:

        # ----------------------------------------------------
        # VALIDATE IMAGE
        # The image is NOT pre-resized — V1 VisionEngine
        # needs full resolution to detect small larvae.
        # ----------------------------------------------------

        img = cv2.imread(image_path)

        if img is None:
            return jsonify({
                "success": False,
                "message": "Invalid or unreadable image file"
            }), 400

        del img
        gc.collect()

        # ----------------------------------------------------
        # PARSE LOCATION
        # ----------------------------------------------------

        try:
            lat_float = float(latitude_raw)  if latitude_raw  is not None else None
            lng_float = float(longitude_raw) if longitude_raw is not None else None
        except (TypeError, ValueError):
            lat_float = None
            lng_float = None

        # ----------------------------------------------------
        # V1 VISION ENGINE
        # If the engine crashes (e.g. a model file is missing
        # on the server) we fall back gracefully so the upload
        # still completes rather than returning a 500 error.
        # ----------------------------------------------------

        try:

            v1_result = vision_engine.analyze(
                image_path=image_path,
                latitude=lat_float,
                longitude=lng_float,
            )

            risk_assessment = v1_result.get("risk_assessment") or {}
            breeding_risk   = risk_assessment.get("breeding_risk") or {}
            risk_level      = breeding_risk.get("level") or "LOW"
            risk_score      = breeding_risk.get("score")  or 0
            v1_route        = v1_result.get("route")
            v1_status       = v1_result.get("status")
            engine_version  = v1_result.get("engine", "vision-engine-v1")

        except Exception as engine_error:

            # Vision engine failed — log it but do not abort
            # the upload so the user report is still saved.
            print("VisionEngine error (fallback):", engine_error)
            traceback.print_exc()

            risk_assessment = {}
            risk_level      = "LOW"
            risk_score      = 0
            v1_route        = "engine_error"
            v1_status       = "engine_error"
            engine_version  = "vision-engine-v1"

        # ----------------------------------------------------
        # CLOUDINARY UPLOAD
        # ----------------------------------------------------

        try:

            upload_result = cloudinary.uploader.upload(
                image_path,
                folder="larvae_lens"
            )
            image_url = upload_result.get("secure_url", "")

        except Exception as cloudinary_error:

            print("Cloudinary error:", cloudinary_error)
            traceback.print_exc()
            image_url = ""

        # ----------------------------------------------------
        # WHATSAPP NOTIFICATION
        # Only send if we have a valid Cloudinary URL.
        # ----------------------------------------------------

        try:

            send_whatsapp_alert(
                user_name,
                risk_level,
                latitude_raw,
                longitude_raw,
                image_url,
            )

        except Exception as whatsapp_error:

            print("WhatsApp error:", whatsapp_error)
            traceback.print_exc()

        # ----------------------------------------------------
        # FIRESTORE REPORT
        # ----------------------------------------------------

        report_data = {

            "image":         unique_filename,
            "image_url":     image_url,
            "latitude":      latitude_raw,
            "longitude":     longitude_raw,
            "timestamp":     timestamp,

            # Flat fields for backward-compat with /reports
            # and /user-reports used by the dashboards.
            "risk_level":    risk_level,
            "risk_score":    risk_score,

            "analysis_method":  "vision-engine-v1",
            "model_version":    engine_version,

            "priority":      priority,
            "email":         email,
            "status":        "PENDING",

            # Full V1 assessment for analytics dashboard.
            "v1_risk_assessment": risk_assessment,
            "v1_route":           v1_route,
            "v1_status":          v1_status,
        }

        db.collection("larvae_reports").add(report_data)

        # ----------------------------------------------------
        # CONSOLE LOGGING
        # ----------------------------------------------------

        print("Risk Level:",  risk_level)
        print("Risk Score:",  risk_score)
        print("V1 Route:",    v1_route)
        print("V1 Status:",   v1_status)
        print("Image:",       unique_filename)
        print("Latitude:",    latitude_raw)
        print("Longitude:",   longitude_raw)
        print("Timestamp:",   timestamp)
        print("UPLOAD SUCCESS")

        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success":          True,
            "message":          "Report uploaded successfully",

            # Flat fields kept for frontend alert display.
            "risk_level":       risk_level,
            "risk_score":       risk_score,
            "analysis_method":  "vision-engine-v1",
            "model_version":    engine_version,

            "latitude":         latitude_raw,
            "longitude":        longitude_raw,

            # Full V1 breakdown (optional — frontend may ignore).
            "risk_assessment":  risk_assessment,
            "v1_route":         v1_route,
            "v1_status":        v1_status,
        })

    except Exception as fatal_error:

        print("Upload route fatal error:", fatal_error)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Internal server error during upload",
            "error":   str(fatal_error)
        }), 500

    finally:

        # Always clean up the temp file.
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as cleanup_error:
                print("Temp file cleanup error:", cleanup_error)


# ============================================================
# V1 ANALYSIS API (stateless — no side-effects)
# ============================================================

def build_api_response(result):
    """
    Convert the internal LarvaeLens V1 engine result into the
    stable JSON contract used by the frontend and database.
    """

    vision      = result.get("vision", {})
    environment = result.get("environment", {})
    risk        = result.get("risk_assessment", {})

    breeding_object = vision.get("breeding_object", {})
    habitat         = vision.get("habitat", {})
    larvae          = vision.get("larvae", {})

    weather    = environment.get("weather", {})
    rainfall   = environment.get("rainfall", {})
    population = environment.get("population", {})
    nearby     = environment.get("nearby_facilities", {})
    hotspot    = environment.get("historical_hotspot", {})

    breeding_risk = risk.get("breeding_risk", {})
    municipal     = risk.get("municipal_intervention_priority", {})

    location = result.get("location", {})

    return {
        "success": True,

        "report": {

            "timestamp": datetime.utcnow().isoformat(),

            "location": {
                "latitude":  location.get("latitude"),
                "longitude": location.get("longitude"),
                "accuracy_m": location.get("accuracy_m")
            },

            "vision": {

                "status": result.get("status"),
                "route":  result.get("route"),

                "breeding_object": {
                    "detected":   breeding_object.get("detected", False),
                    "confidence": breeding_object.get("confidence", 0.0)
                },

                "habitat": {
                    "detected":   habitat.get("detected", False),
                    "type":       habitat.get("type"),
                    "confidence": habitat.get("confidence"),

                    "bounding_box": {
                        "area_pixels":      habitat.get("bounding_box_area"),
                        "coverage_percent": habitat.get("bounding_box_coverage_percent")
                    },

                    "segmentation": {
                        "area_pixels":      habitat.get("segmentation_area"),
                        "coverage_percent": habitat.get("segmentation_coverage_percent"),
                        "mask_ratio":       habitat.get("mask_ratio")
                    }
                },

                "larvae": {
                    "detected":                larvae.get("detected", False),
                    "count":                   larvae.get("count", 0),
                    "non_larvae_count":        larvae.get("non_larvae_count", 0),
                    "confidence":              larvae.get("confidence", 0.0),
                    "density_per_10000_pixels": larvae.get("density_per_10000_pixels", 0.0),
                    "source":                  larvae.get("source")
                }
            },

            "environment": {

                "weather": {
                    "temperature_c":    weather.get("temperature_c"),
                    "humidity_percent": weather.get("humidity_percent")
                },

                "rainfall": {
                    "24h_mm": rainfall.get("24h_mm"),
                    "3d_mm":  rainfall.get("3d_mm"),
                    "7d_mm":  rainfall.get("7d_mm")
                },

                "population": {
                    "radius_m":             population.get("radius_m"),
                    "estimated_population": population.get("estimated_population"),
                    "density_per_km2":      population.get("density_per_km2")
                },

                "nearby_facilities": {
                    "schools_500m":         nearby.get("schools_500m"),
                    "hospitals_500m":       nearby.get("hospitals_500m"),
                    "higher_education_500m": nearby.get("higher_education_500m")
                },

                "historical_hotspot": {
                    "status":           hotspot.get("status"),
                    "hotspots_500m":    hotspot.get("hotspots_500m"),
                    "nearest_hotspot_m": hotspot.get("nearest_hotspot_m"),
                    "historical_cases": hotspot.get("historical_cases")
                }
            },

            "risk": {

                "breeding": {
                    "score":     breeding_risk.get("score"),
                    "max_score": breeding_risk.get("max_score", 100),
                    "level":     breeding_risk.get("level")
                },

                "municipal": {
                    "score":     municipal.get("score"),
                    "max_score": municipal.get("max_score", 100),
                    "level":     municipal.get("level"),
                    "status":    municipal.get("status")
                }
            },

            "workflow": {
                "status":       "PENDING",
                "display_flag": "RED"
            }
        }
    }


@app.route(
    "/api/analyze",
    methods=["POST"]
)
def api_analyze():
    """
    LarvaeLens V1 stateless analysis endpoint.
    Does NOT write to Firestore / Cloudinary / WhatsApp.
    """

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image = request.files.get("image")

    if image is None:

        return jsonify({
            "success": False,
            "message": "No image provided"
        }), 400

    # --------------------------------------------------------
    # FILE SIZE
    # --------------------------------------------------------

    if (
        image.content_length
        and image.content_length > 5 * 1024 * 1024
    ):

        return jsonify({
            "success": False,
            "message": "Image too large"
        }), 400

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    latitude  = request.form.get("latitude")
    longitude = request.form.get("longitude")
    accuracy_m = request.form.get("accuracy_m")

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Latitude and longitude are required"
        }), 400

    try:
        latitude   = float(latitude)
        longitude  = float(longitude)
        if accuracy_m is not None:
            accuracy_m = float(accuracy_m)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid location values"
        }), 400

    # --------------------------------------------------------
    # SAVE TEMP IMAGE
    # --------------------------------------------------------

    original_filename = image.filename or "uploaded_image.jpg"
    unique_filename   = f"{uuid.uuid4()}_{original_filename}"
    image_path        = os.path.join(UPLOAD_FOLDER, unique_filename)

    try:

        image.save(image_path)

        img = cv2.imread(image_path)

        if img is None:

            return jsonify({
                "success": False,
                "message": "Invalid image"
            }), 400

        del img
        gc.collect()

        result = vision_engine.analyze(
            image_path=image_path,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
        )

        return jsonify({
            "success": True,
            "result":  result
        })

    except Exception as e:

        print("LarvaeLens V1 API Error:", e)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Analysis failed",
            "error":   str(e)
        }), 500

    finally:

        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as cleanup_error:
                print("Image cleanup error:", cleanup_error)


# ============================================================
# GET ALL REPORTS
# Sorted by Firestore server-side (no in-memory sort).
# Limited to 200 most recent docs to prevent OOM.
# ============================================================

@app.route(
    "/reports",
    methods=["GET"]
)
def get_reports():

    reports = []

    docs = (
        db.collection("larvae_reports")
        .order_by("timestamp", direction=Query.DESCENDING)
        .limit(200)
        .stream()
    )

    for doc_ref in docs:

        doc = doc_ref.to_dict()

        reports.append({
            "id":              doc_ref.id,
            "image":           doc.get("image"),
            "image_url":       doc.get("image_url", ""),
            "risk_level":      doc.get("risk_level"),
            "risk_score":      doc.get("risk_score"),
            "analysis_method": doc.get("analysis_method"),
            "model_version":   doc.get("model_version"),
            "status":          doc.get("status"),
            "latitude":        doc.get("latitude"),
            "longitude":       doc.get("longitude"),
            "priority":        doc.get("priority"),
            "timestamp":       doc.get("timestamp"),
        })

    return jsonify(reports)


# ============================================================
# UPDATE REPORT STATUS
# ============================================================

@app.route(
    "/update-status/<doc_id>",
    methods=["PUT"]
)
def update_status(doc_id):

    status = request.json.get("status", "COMPLETED") if request.json else "COMPLETED"

    try:

        db.collection("larvae_reports").document(doc_id).update({
            "status": status
        })

        return jsonify({
            "message": "Status Updated",
            "status":  status
        })

    except NotFound:

        return jsonify({
            "success": False,
            "message": f"Report {doc_id} not found"
        }), 404

    except Exception as e:

        print("update-status error:", e)
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": "Failed to update status",
            "error":   str(e)
        }), 500


# ============================================================
# LOGIN (OAuth placeholder)
# ============================================================

@app.route("/login")
def login():

    authorization_url = "YOUR_AUTHORIZATION_URL"

    return redirect(authorization_url)


# ============================================================
# CALLBACK (OAuth placeholder)
# ============================================================

@app.route("/callback")
def callback():

    code = request.args.get("code")

    print("Authorization Code:", code)

    return redirect("http://127.0.0.1:5500/dashboard.html")


# ============================================================
# SIGNUP
# Passwords are hashed with werkzeug before saving.
# ============================================================

@app.route(
    "/signup",
    methods=["POST"]
)
def signup():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"success": False, "message": "Invalid JSON body"}), 400

    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "name, email and password are required"
        }), 400

    existing_users = list(
        db.collection("users")
        .where(
            filter=firebase_admin.firestore.FieldFilter("email", "==", email)
        )
        .stream()
    )

    if len(existing_users) > 0:
        return jsonify({
            "success": False,
            "message": "Email already exists"
        })

    hashed_password = generate_password_hash(password)

    db.collection("users").add({
        "name":     name,
        "email":    email,
        "password": hashed_password,
    })

    return jsonify({
        "success": True,
        "message": "User Registered Successfully"
    })


# ============================================================
# LOGIN USER
# Uses check_password_hash to verify hashed passwords.
# ============================================================

@app.route(
    "/login-user",
    methods=["POST"]
)
def login_user():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"success": False, "message": "Invalid JSON body"}), 400

    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "email and password are required"
        }), 400

    users_ref = (
        db.collection("users")
        .where(
            filter=firebase_admin.firestore.FieldFilter("email", "==", email)
        )
        .stream()
    )

    users_list = list(users_ref)

    if len(users_list) == 0:
        return jsonify({
            "success": False,
            "message": "Invalid Credentials"
        })

    user = users_list[0].to_dict()

    # Support both hashed passwords (new) and plain text (legacy).
    stored_password = user.get("password", "")

    password_ok = (
        check_password_hash(stored_password, password)
        if stored_password.startswith("pbkdf2:") or stored_password.startswith("scrypt:")
        else stored_password == password
    )

    if not password_ok:
        return jsonify({
            "success": False,
            "message": "Invalid Credentials"
        })

    return jsonify({
        "success": True,
        "message": "Login Successful",
        "name":    user.get("name"),
        "email":   user.get("email"),
    })


# ============================================================
# USER REPORTS
# Sorted server-side by timestamp descending.
# ============================================================

@app.route(
    "/user-reports/<email>",
    methods=["GET"]
)
def user_reports(email):

    reports = []

    docs = (
        db.collection("larvae_reports")
        .where(
            filter=firebase_admin.firestore.FieldFilter("email", "==", email)
        )
        .order_by("timestamp", direction=Query.DESCENDING)
        .limit(100)
        .stream()
    )

    for doc_ref in docs:

        doc = doc_ref.to_dict()

        reports.append({
            "risk_level": doc.get("risk_level"),
            "risk_score": doc.get("risk_score"),
            "status":     doc.get("status"),
            "timestamp":  doc.get("timestamp"),
            "image_url":  doc.get("image_url", ""),
        })

    return jsonify(reports)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    app.run(debug=False)