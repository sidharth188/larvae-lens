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
# EXISTING UPLOAD ROUTE
# ============================================================

@app.route("/upload", methods=["POST"])
def upload():

    image = request.files.get("image")

    if image is None:

        return jsonify({
            "message": "No image provided"
        }), 400

    if (
        image.content_length
        and image.content_length > 5 * 1024 * 1024
    ):

        return jsonify({
            "message": "Image too large"
        }), 400

    latitude = request.form.get("latitude")

    longitude = request.form.get("longitude")

    timestamp = datetime.utcnow().isoformat()

    priority = request.form.get(
        "priority"
    )

    email = request.form.get("email", "")

    user_name = request.form.get("user_name", "")

    unique_filename = (
        f"{uuid.uuid4()}_{image.filename or 'image.jpg'}"
    )

    image_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    image.save(
        image_path
    )

    # --------------------------------------------------------
    # Validate the uploaded file is a readable image.
    # The image is NOT resized before analysis — the V1
    # VisionEngine requires full resolution to reliably
    # detect small larvae and habitat masks.
    # --------------------------------------------------------

    img = cv2.imread(
        image_path
    )

    if img is None:

        if os.path.exists(image_path):
            os.remove(image_path)

        return jsonify({
            "message": "Invalid image"
        }), 400

    del img
    gc.collect()

    # --------------------------------------------------------
    # V1 Vision Engine pipeline.
    # Replaces the legacy rule-based CV classifier.
    # The engine runs 4 YOLO models plus the Environmental
    # and Risk engines to produce a structured result.
    # --------------------------------------------------------

    try:
        lat_float = float(latitude) if latitude is not None else None
        lng_float = float(longitude) if longitude is not None else None
    except (TypeError, ValueError):
        lat_float = None
        lng_float = None

    v1_result = vision_engine.analyze(
        image_path=image_path,
        latitude=lat_float,
        longitude=lng_float,
    )

    # --------------------------------------------------------
    # Extract a flat risk_level / risk_score from the V1
    # result for backward compatibility with the frontend.
    # --------------------------------------------------------

    risk_assessment = v1_result.get("risk_assessment") or {}

    breeding_risk = risk_assessment.get("breeding_risk") or {}

    risk_level = (
        breeding_risk.get("level")
        or "LOW"
    )

    risk_score = (
        breeding_risk.get("score")
        or 0
    )

    try:

        upload_result = (
            cloudinary.uploader.upload(
                image_path,
                folder="larvae_lens"
            )
        )

        image_url = upload_result.get(
            "secure_url"
        )

    except Exception as e:

        print(
            "Cloudinary Error:",
            e
        )

        return jsonify({
            "message":
                "Failed to upload image to cloud"
        }), 500

    finally:

        if os.path.exists(
            image_path
        ):

            os.remove(
                image_path
            )

    # --------------------------------------------------------
    # WhatsApp notification
    # --------------------------------------------------------

    try:

        send_whatsapp_alert(
            user_name,
            risk_level,
            latitude,
            longitude,
            image_url,
        )

    except Exception as e:

        print(
            "WhatsApp Error:",
            e
        )

        traceback.print_exc()

    # --------------------------------------------------------
    # Firestore report
    # --------------------------------------------------------

    report_data = {

        "image":
            unique_filename,

        "latitude":
            latitude,

        "longitude":
            longitude,

        "timestamp":
            timestamp,

        # Flat fields kept for backward compatibility
        # with the existing /reports and /user-reports
        # endpoints used by the dashboard.
        "risk_level":
            risk_level,

        "risk_score":
            risk_score,

        "analysis_method":
            "vision-engine-v1",

        "model_version":
            v1_result.get("engine", "vision-engine-v1"),

        "priority":
            priority,

        "email":
            email,

        "status":
            "PENDING",

        # Full V1 risk assessment stored for analytics.
        "v1_risk_assessment":
            risk_assessment,

        "v1_route":
            v1_result.get("route"),

        "v1_status":
            v1_result.get("status"),
    }

    db.collection(
        "larvae_reports"
    ).add(
        report_data
    )

    # --------------------------------------------------------
    # Console logging
    # --------------------------------------------------------

    print(
        "Risk Level:",
        risk_level
    )

    print(
        "Risk Score:",
        risk_score
    )

    print(
        "V1 Route:",
        v1_result.get("route")
    )

    print(
        "V1 Status:",
        v1_result.get("status")
    )

    print(
        "Image Saved:",
        unique_filename
    )

    print(
        "Latitude:",
        latitude
    )

    print(
        "Longitude:",
        longitude
    )

    print(
        "Timestamp:",
        timestamp
    )

    print(
        "UPLOAD SUCCESS"
    )

    return jsonify({

        "message":
            "Report uploaded successfully",

        # Flat fields for frontend backward compatibility.
        "risk_level":
            risk_level,

        "risk_score":
            risk_score,

        "analysis_method":
            "vision-engine-v1",

        "model_version":
            v1_result.get("engine", "vision-engine-v1"),

        "latitude":
            latitude,

        "longitude":
            longitude,

        # Full V1 risk breakdown for any frontend that wants it.
        "risk_assessment":
            risk_assessment,

        "v1_route":
            v1_result.get("route"),

        "v1_status":
            v1_result.get("status"),
    })


# ============================================================
# NEW LARVAELENS V1 ANALYSIS API
# ============================================================
def build_api_response(result):
    """
    Convert the internal LarvaeLens V1 engine result into the
    stable JSON contract used by the frontend and database.
    """

    vision = result.get("vision", {})
    environment = result.get("environment", {})
    risk = result.get("risk_assessment", {})

    breeding_object = vision.get(
        "breeding_object",
        {}
    )

    habitat = vision.get(
        "habitat",
        {}
    )

    larvae = vision.get(
        "larvae",
        {}
    )

    weather = environment.get(
        "weather",
        {}
    )

    rainfall = environment.get(
        "rainfall",
        {}
    )

    population = environment.get(
        "population",
        {}
    )

    nearby = environment.get(
        "nearby_facilities",
        {}
    )

    hotspot = environment.get(
        "historical_hotspot",
        {}
    )

    breeding_risk = risk.get(
        "breeding_risk",
        {}
    )

    municipal = risk.get(
        "municipal_intervention_priority",
        {}
    )

    location = result.get(
        "location",
        {}
    )

    return {
        "success": True,

        "report": {

            "timestamp": datetime.utcnow().isoformat(),

            "location": {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "accuracy_m": location.get("accuracy_m")
            },

            "vision": {

                "status": result.get("status"),
                "route": result.get("route"),

                "breeding_object": {
                    "detected": breeding_object.get("detected", False),
                    "confidence": breeding_object.get("confidence", 0.0)
                },

                "habitat": {
                    "detected": habitat.get("detected", False),
                    "type": habitat.get("type"),
                    "confidence": habitat.get("confidence"),

                    "bounding_box": {
                        "area_pixels": habitat.get("bounding_box_area"),
                        "coverage_percent": habitat.get("bounding_box_coverage_percent")
                    },

                    "segmentation": {
                        "area_pixels": habitat.get("segmentation_area"),
                        "coverage_percent": habitat.get("segmentation_coverage_percent"),
                        "mask_ratio": habitat.get("mask_ratio")
                    }
                },

                "larvae": {
                    "detected": larvae.get("detected", False),
                    "count": larvae.get("count", 0),
                    "non_larvae_count": larvae.get("non_larvae_count", 0),
                    "confidence": larvae.get("confidence", 0.0),
                    "density_per_10000_pixels": larvae.get("density_per_10000_pixels", 0.0),
                    "source": larvae.get("source")
                }
            },

            "environment": {

                "weather": {
                    "temperature_c": weather.get("temperature_c"),
                    "humidity_percent": weather.get("humidity_percent")
                },

                "rainfall": {
                    "24h_mm": rainfall.get("24h_mm"),
                    "3d_mm": rainfall.get("3d_mm"),
                    "7d_mm": rainfall.get("7d_mm")
                },

                "population": {
                    "radius_m": population.get("radius_m"),
                    "estimated_population": population.get("estimated_population"),
                    "density_per_km2": population.get("density_per_km2")
                },

                "nearby_facilities": {
                    "schools_500m": nearby.get("schools_500m"),
                    "hospitals_500m": nearby.get("hospitals_500m"),
                    "higher_education_500m": nearby.get("higher_education_500m")
                },

                "historical_hotspot": {
                    "status": hotspot.get("status"),
                    "hotspots_500m": hotspot.get("hotspots_500m"),
                    "nearest_hotspot_m": hotspot.get("nearest_hotspot_m"),
                    "historical_cases": hotspot.get("historical_cases")
                }
            },

            "risk": {

                "breeding": {
                    "score": breeding_risk.get("score"),
                    "max_score": breeding_risk.get("max_score", 100),
                    "level": breeding_risk.get("level")
                },

                "municipal": {
                    "score": municipal.get("score"),
                    "max_score": municipal.get("max_score", 100),
                    "level": municipal.get("level"),
                    "status": municipal.get("status")
                }
            },

            "workflow": {
                "status": "PENDING",
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
    LarvaeLens V1 analysis endpoint.

    Input:

        image
        latitude
        longitude
        accuracy_m

    Pipeline:

        Image
          ↓
        Vision Engine
          ↓
        Environmental Engine
          ↓
        Risk Engine
          ↓
        JSON

    This endpoint DOES NOT write to Firestore yet.

    It is intentionally separated from the existing
    /upload route so we can test V1 safely.
    """

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image = request.files.get(
        "image"
    )

    if image is None:

        return jsonify({

            "success": False,

            "message":
                "No image provided"

        }), 400

    # --------------------------------------------------------
    # FILE SIZE
    # --------------------------------------------------------

    if (
        image.content_length
        and image.content_length
        > 5 * 1024 * 1024
    ):

        return jsonify({

            "success": False,

            "message":
                "Image too large"

        }), 400

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    latitude = request.form.get(
        "latitude"
    )

    longitude = request.form.get(
        "longitude"
    )

    accuracy_m = request.form.get(
        "accuracy_m"
    )

    if (
        latitude is None
        or longitude is None
    ):

        return jsonify({

            "success": False,

            "message":
                "Latitude and longitude are required"

        }), 400

    # --------------------------------------------------------
    # CONVERT LOCATION
    # --------------------------------------------------------

    try:

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

        if accuracy_m is not None:

            accuracy_m = float(
                accuracy_m
            )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "success": False,

            "message":
                "Invalid location values"

        }), 400

    # --------------------------------------------------------
    # SAVE TEMPORARY IMAGE
    # --------------------------------------------------------

    original_filename = (
        image.filename
        or "uploaded_image.jpg"
    )

    unique_filename = (
        f"{uuid.uuid4()}_"
        f"{original_filename}"
    )

    image_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    try:

        image.save(
            image_path
        )

        # ----------------------------------------------------
        # VALIDATE IMAGE
        # ----------------------------------------------------

        img = cv2.imread(
            image_path
        )

        if img is None:

            return jsonify({

                "success": False,

                "message":
                    "Invalid image"

            }), 400

        del img

        gc.collect()

        # ----------------------------------------------------
        # RUN VISION ENGINE V1
        # ----------------------------------------------------

        result = (
            vision_engine.analyze(

                image_path=image_path,

                latitude=latitude,

                longitude=longitude,

                accuracy_m=accuracy_m,
            )
        )

        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "result": result

        })

    except Exception as e:

        print(
            "LarvaeLens V1 API Error:",
            e
        )

        traceback.print_exc()

        return jsonify({

            "success": False,

            "message":
                "Analysis failed",

            "error":
                str(e)

        }), 500

    finally:

        # ----------------------------------------------------
        # REMOVE TEMPORARY IMAGE
        # ----------------------------------------------------

        if os.path.exists(
            image_path
        ):

            try:

                os.remove(
                    image_path
                )

            except Exception as cleanup_error:

                print(
                    "Image cleanup error:",
                    cleanup_error
                )


# ============================================================
# GET ALL REPORTS
# ============================================================

@app.route(
    "/reports",
    methods=["GET"]
)
def get_reports():

    reports = []

    docs = (
        db.collection(
            "larvae_reports"
        ).stream()
    )

    for doc_ref in docs:

        doc = (
            doc_ref.to_dict()
        )

        reports.append({

            "id":
                doc_ref.id,

            "image":
                doc.get("image"),

            "risk_level":
                doc.get("risk_level"),

            "risk_score":
                doc.get("risk_score"),

            "analysis_method":
                doc.get("analysis_method"),

            "model_version":
                doc.get("model_version"),

            "evidence":
                doc.get(
                    "evidence",
                    []
                ),

            "status":
                doc.get("status"),

            "latitude":
                doc.get("latitude"),

            "longitude":
                doc.get("longitude"),

            "priority":
                doc.get("priority"),

            "timestamp":
                doc.get("timestamp"),
        })

    reports.sort(
        key=lambda x:
            x.get(
                "timestamp",
                ""
            ),
        reverse=True
    )

    return jsonify(
        reports
    )


# ============================================================
# UPDATE REPORT STATUS
# ============================================================

@app.route(
    "/update-status/<doc_id>",
    methods=["PUT"]
)
def update_status(
    doc_id
):

    db.collection(
        "larvae_reports"
    ).document(
        doc_id
    ).update({

        "status":
            "COMPLETED"

    })

    return jsonify({

        "message":
            "Status Updated"

    })


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login"
)
def login():

    authorization_url = (
        "YOUR_AUTHORIZATION_URL"
    )

    return redirect(
        authorization_url
    )


# ============================================================
# CALLBACK
# ============================================================

@app.route(
    "/callback"
)
def callback():

    code = request.args.get(
        "code"
    )

    print(
        "Authorization Code:",
        code
    )

    return redirect(
        "http://127.0.0.1:5500/dashboard.html"
    )


# ============================================================
# SIGNUP
# ============================================================

@app.route(
    "/signup",
    methods=["POST"]
)
def signup():

    data = request.json

    name = data[
        "name"
    ]

    email = data[
        "email"
    ]

    password = data[
        "password"
    ]

    existing_users = list(

        db.collection(
            "users"
        ).where(

            filter=
                firebase_admin.firestore.FieldFilter(
                    "email",
                    "==",
                    email
                )

        ).stream()
    )

    if len(
        existing_users
    ) > 0:

        return jsonify({

            "success":
                False,

            "message":
                "Email already exists",

        })

    db.collection(
        "users"
    ).add({

        "name":
            name,

        "email":
            email,

        "password":
            password,

    })

    return jsonify({

        "success":
            True,

        "message":
            "User Registered Successfully",

    })


# ============================================================
# LOGIN USER
# ============================================================

@app.route(
    "/login-user",
    methods=["POST"]
)
def login_user():

    data = request.json

    email = data[
        "email"
    ]

    password = data[
        "password"
    ]

    users_ref = (

        db.collection(
            "users"
        )

        .where(

            filter=
                firebase_admin.firestore.FieldFilter(
                    "email",
                    "==",
                    email
                )

        )

        .where(

            filter=
                firebase_admin.firestore.FieldFilter(
                    "password",
                    "==",
                    password
                )

        )

        .stream()
    )

    users_list = list(
        users_ref
    )

    if len(
        users_list
    ) > 0:

        user = (
            users_list[0].to_dict()
        )

        return jsonify({

            "success":
                True,

            "message":
                "Login Successful",

            "name":
                user.get(
                    "name"
                ),

            "email":
                user.get(
                    "email"
                ),

        })

    return jsonify({

        "success":
            False,

        "message":
            "Invalid Credentials",

    })


# ============================================================
# USER REPORTS
# ============================================================

@app.route(
    "/user-reports/<email>",
    methods=["GET"]
)
def user_reports(
    email
):

    reports = []

    docs = (

        db.collection(
            "larvae_reports"
        )

        .where(

            filter=
                firebase_admin.firestore.FieldFilter(
                    "email",
                    "==",
                    email
                )

        )

        .stream()
    )

    for doc_ref in docs:

        doc = (
            doc_ref.to_dict()
        )

        reports.append({

            "risk_level":
                doc.get(
                    "risk_level"
                ),

            "risk_score":
                doc.get(
                    "risk_score"
                ),

            "evidence":
                doc.get(
                    "evidence",
                    []
                ),

            "status":
                doc.get(
                    "status"
                ),

            "timestamp":
                doc.get(
                    "timestamp"
                ),

        })

    reports.reverse()

    return jsonify(
        reports
    )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=False
    )