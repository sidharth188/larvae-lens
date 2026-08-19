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
      5. Send WhatsApp alert for HIGH risk.
      6. Upsert user profile in `users` collection.
      7. Save full structured report to `larvae_reports` collection.
      8. Return flat JSON for frontend display.
    """

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image = request.files.get("image")

    if image is None:
        return jsonify({"success": False, "message": "No image provided"}), 400

    if image.content_length and image.content_length > 5 * 1024 * 1024:
        return jsonify({"success": False, "message": "Image too large (max 5 MB)"}), 400

    # --------------------------------------------------------
    # FORM FIELDS
    # --------------------------------------------------------

    latitude_raw  = request.form.get("latitude")
    longitude_raw = request.form.get("longitude")
    accuracy_raw  = request.form.get("accuracy_m")
    timestamp     = datetime.utcnow().isoformat()
    priority      = request.form.get("priority", "false")
    priority = str(priority_raw).strip().lower() == "true"
    email         = request.form.get("email", "").strip()
    user_name     = request.form.get("user_name", "").strip()

    # --------------------------------------------------------
    # ALL PROCESSING IN TRY BLOCK
    # --------------------------------------------------------

    image_path = None

    try:
        # SAVE TEMP FILE
        unique_filename = f"{uuid.uuid4()}_{image.filename or 'image.jpg'}"
        image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        image.save(image_path)

        image_url = ""

        # ----------------------------------------------------
        # VALIDATE IMAGE

        # ----------------------------------------------------

        img = cv2.imread(image_path)
        if img is None:
            return jsonify({"success": False, "message": "Invalid or unreadable image file"}), 400
        del img
        gc.collect()

        # ----------------------------------------------------
        # PARSE LOCATION
        # ----------------------------------------------------

        try:
            lat_float  = float(latitude_raw)  if latitude_raw  else None
            lng_float  = float(longitude_raw) if longitude_raw else None
            acc_float  = float(accuracy_raw)  if accuracy_raw  else None
        except (TypeError, ValueError):
            lat_float = lng_float = acc_float = None

        # ----------------------------------------------------
        # V1 VISION ENGINE
        # Falls back gracefully if a model file is missing.
        # ----------------------------------------------------

        try:
            v1_result = vision_engine.analyze(
                image_path=image_path,
                latitude=lat_float,
                longitude=lng_float,
                accuracy_m=acc_float,
            )
        except Exception as engine_error:
            print("VisionEngine error (fallback):", engine_error)
            traceback.print_exc()
            v1_result = {
                "engine": "vision-engine-v1",
                "status": "engine_error",
                "route":  "engine_error",
                "model1": {"detected": False, "objects": [], "confidence": 0.0},
                "model2": None,
                "model3": None,
                "model4": None,
                "environment": {},
                "risk_assessment": {},
            }

        # ----------------------------------------------------
        # UNPACK V1 RESULT into the exact target schema
        # ----------------------------------------------------

        env_raw         = v1_result.get("environment") or {}
        weather_raw     = env_raw.get("weather")       or {}
        population_raw  = env_raw.get("population")    or {}
        facilities_raw  = env_raw.get("nearby_facilities") or {}
        hist_raw        = env_raw.get("historical_risk")   or {}
        loc_raw         = env_raw.get("location")      or {}

        risk_raw        = v1_result.get("risk_assessment") or {}
        breeding_risk   = risk_raw.get("breeding_risk")    or {}

        model1_raw = v1_result.get("model1") or {}
        model2_raw = v1_result.get("model2")        # may be None
        model3_raw = v1_result.get("model3")        # may be None
        model4_raw = v1_result.get("model4") or {}

        risk_level = breeding_risk.get("level") or "LOW"
        risk_score = breeding_risk.get("score") or 0

        # ---- vision sub-document ----
        vision_doc = {
            "engine":       v1_result.get("engine", "vision-engine-v1"),
            "final_status": v1_result.get("status"),
            "route":        v1_result.get("route"),
            "model1": {
                "detected":   model1_raw.get("detected", False),
                "objects":    model1_raw.get("objects", []),
                "confidence": model1_raw.get("confidence", 0.0),
            },
            "model2": (
                {
                    "water_detected": model2_raw.get("water_detected", False),
                    "objects":        model2_raw.get("objects", []),
                    "confidence":     model2_raw.get("confidence", 0.0),
                }
                if model2_raw is not None else None
            ),
            "model3": (
                {
                    "detected":   model3_raw.get("detected", False),
                    "classes":    model3_raw.get("classes", []),
                    "confidence": model3_raw.get("confidence", 0.0),
                }
                if model3_raw is not None else None
            ),
            "model4": (
                {
                    "detected":                      model4_raw.get("detected", False),
                    "larvae_count":                  model4_raw.get("larvae_count", 0),
                    "non_larvae_count":              model4_raw.get("non_larvae_count", 0),
                    "larvae_density_per_10000_pixels": model4_raw.get("larvae_density_per_10000_pixels", 0.0),
                    "confidence":                    model4_raw.get("confidence", 0.0),
                }
                if model4_raw else None
            ),
        }

        # ---- environment sub-document ----
        environment_doc = {
            "temperature_c":           weather_raw.get("temperature_c"),
            "humidity_percent":        weather_raw.get("humidity_percent"),
            "rainfall_24h_mm":         weather_raw.get("rainfall_24h_mm"),
            "rainfall_3d_mm":          weather_raw.get("rainfall_3d_mm"),
            "rainfall_7d_mm":          weather_raw.get("rainfall_7d_mm"),
            "current_precipitation_mm": weather_raw.get("current_precipitation_mm"),
            "source":                  weather_raw.get("source"),
            "weather_timezone":        weather_raw.get("weather_timezone"),
        }

        # ---- location sub-document ----
        location_doc = {
            "latitude":   loc_raw.get("latitude")  or lat_float,
            "longitude":  loc_raw.get("longitude") or lng_float,
            "accuracy_m": loc_raw.get("accuracy_m") or acc_float,
        }

        # ---- population sub-document ----
        population_doc = {
            "search_radius_m":             population_raw.get("search_radius_m"),
            "estimated_population_500m":   population_raw.get("estimated_population_500m"),
            "population_density_500m":     population_raw.get("population_density_500m"),
            "area_km2":                    population_raw.get("area_km2"),
            "data_year":                   population_raw.get("data_year"),
            "resolution":                  population_raw.get("resolution"),
            "source":                      population_raw.get("source"),
        }

        # ---- nearby_facilities sub-document ----
        def _spatial(raw, key):
            return (raw.get(key) or {}).get("spatial_summary") or {}

        schools_spatial    = _spatial(facilities_raw, "schools")
        hospitals_spatial  = _spatial(facilities_raw, "hospitals")
        higher_ed_spatial  = _spatial(facilities_raw, "higher_education")

        nearby_facilities_doc = {
            "search_radius_m": facilities_raw.get("search_radius_m"),
            "schools": {
                "within_250m": schools_spatial.get("within_250m", 0),
                "within_500m": schools_spatial.get("within_500m", 0),
                "within_1km":  schools_spatial.get("within_1km",  0),
            },
            "hospitals": {
                "within_250m": hospitals_spatial.get("within_250m", 0),
                "within_500m": hospitals_spatial.get("within_500m", 0),
                "within_1km":  hospitals_spatial.get("within_1km",  0),
            },
            "universities": {
                "within_250m": higher_ed_spatial.get("within_250m", 0),
                "within_500m": higher_ed_spatial.get("within_500m", 0),
                "within_1km":  higher_ed_spatial.get("within_1km",  0),
            },
            "source": facilities_raw.get("provider", "Google Places API (New)"),
        }

        # ---- historical_risk sub-document ----
        historical_risk_doc = {
            "search_radius_m":               hist_raw.get("search_radius_m", 500),
            "hotspots_within_500m":          hist_raw.get("hotspots_within_500m"),
            "nearest_hotspot_distance_m":    hist_raw.get("nearest_hotspot_distance_m"),
            "historical_cases_within_500m":  hist_raw.get("historical_cases_within_500m"),
            "most_recent_hotspot_year":      hist_raw.get("most_recent_hotspot_year"),
            "source":                        hist_raw.get("source", "LarvaeLens historical database"),
        }

        # ---- risk sub-document ----
        risk_doc = {
            "engine":              risk_raw.get("risk_engine", "risk-engine-v1"),
            "biological_score":    risk_raw.get("biological_score"),
            "environmental_score": risk_raw.get("environmental_score"),
            "population_score":    risk_raw.get("population_score"),
            "facility_score":      risk_raw.get("facility_score"),
            "historical_score":    risk_raw.get("historical_score"),
            "final_score":         breeding_risk.get("score"),
            "risk_level":          risk_level,
            "generated_at":        timestamp,
        }
        # ---- risk sub-document ----
        municipal_priority = (
            risk_raw.get("municipal_priority") or {}
        )

        breeding_components = (
            breeding_risk.get("components") or {}
        )

        municipal_components = (
            municipal_priority.get("components") or {}
        )

        risk_doc = {
            "engine": risk_raw.get(
                "risk_engine",
                "risk-engine-v1"
           ),

           # -----------------------------------------
           # BREEDING RISK
           # -----------------------------------------
           "breeding_risk": {
               "score": breeding_risk.get("score"),
               "level": breeding_risk.get("level"),
               "base_level": breeding_risk.get("base_level"),
               "maximum": breeding_risk.get(
                   "maximum",
                   100
               ),
               "escalation_reasons":
                   breeding_risk.get(
                       "escalation_reasons",
                       []
                   ),
                "components": breeding_components,
           },

           # -----------------------------------------
           # MUNICIPAL INTERVENTION PRIORITY
           # -----------------------------------------
           "municipal_priority": {
               "score": municipal_priority.get("score"),
               "level": municipal_priority.get("level"),
               "maximum": municipal_priority.get(
                   "maximum",
                   100
               ),
               "normalized_from_available_evidence":
                   municipal_priority.get(
                      "normalized_from_available_evidence",
                      False
                   ),
               "unavailable_components":
                   municipal_priority.get(
                       "unavailable_components",
                       []
                   ),
                "components": municipal_components,
           },

           # -----------------------------------------
           # QUICK-ACCESS SCORES
           # -----------------------------------------
           "final_score":
               breeding_risk.get("score"),

           "risk_level":
               breeding_risk.get("level"),

           "municipal_score":
               municipal_priority.get("score"),

            "municipal_level":
               municipal_priority.get("level"),
        }

        # ----------------------------------------------------
        # CLOUDINARY UPLOAD
        # ----------------------------------------------------

        try:
            upload_result = cloudinary.uploader.upload(image_path, folder="larvae_lens")
            image_url = upload_result.get("secure_url", "")
        except Exception as cloudinary_error:
            print("Cloudinary error:", cloudinary_error)
            traceback.print_exc()
            image_url = ""

        # ----------------------------------------------------
        # WHATSAPP ALERT (HIGH risk only)
        # ----------------------------------------------------

        try:
            if risk_level == "HIGH":
                send_whatsapp_alert(user_name, risk_level, latitude_raw, longitude_raw, image_url)
        except Exception as whatsapp_error:
            print("WhatsApp error:", whatsapp_error)

        # ----------------------------------------------------
        # UPSERT USER PROFILE in `users` collection
        # ----------------------------------------------------

        try:
            if email:
                existing = list(
                    db.collection("users")
                    .where(filter=firebase_admin.firestore.FieldFilter("email", "==", email))
                    .limit(1)
                    .stream()
                )
                if not existing:
                    db.collection("users").add({
                        "name":  user_name,
                        "email": email,
                    })
        except Exception as user_upsert_error:
            print("User upsert error:", user_upsert_error)

        # ----------------------------------------------------
        # SAVE FULL STRUCTURED REPORT to `larvae_reports`
        # ----------------------------------------------------

        report_data = {
            # ---- metadata ----
            "timestamp":     timestamp,
            "image_url":     image_url,
            "image":         unique_filename,
            "priority":      priority,
            "status":        "PENDING",

            # ---- user identity ----
            "email":         email,
            "user_name":     user_name,

            # ---- flat risk fields (for quick dashboard queries) ----
            "risk_level":    risk_level,
            "risk_score":    risk_score,

            # ---- full nested analysis ----
            "vision":             vision_doc,
            "environment":        environment_doc,
            "location":           location_doc,
            "population":         population_doc,
            "nearby_facilities":  nearby_facilities_doc,
            "historical_risk":    historical_risk_doc,
            "risk":               risk_doc,
        }

        _ts, report_ref = db.collection("larvae_reports").add(report_data)
        report_id = report_ref.id

        # ----------------------------------------------------
        # LOGGING
        # ----------------------------------------------------

        print("=== UPLOAD SUCCESS ===")
        print("Report ID:  ", report_id)
        print("Risk Level: ", risk_level)
        print("Risk Score: ", risk_score)
        print("V1 Route:   ", v1_result.get("route"))
        print("V1 Status:  ", v1_result.get("status"))
        print("Image URL:  ", image_url)

        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return jsonify({
            "success":         True,
            "message":         "Report uploaded successfully",
            "report_id":       report_id,

            # flat fields for the frontend alert
            "risk_level":      risk_level,
            "risk_score":      risk_score,
            "image_url":       image_url,

            # detailed breakdown (optional — frontend may use for analytics)
            "vision":          vision_doc,
            "risk":            risk_doc,
            "environment":     environment_doc,
            "location":        location_doc,
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

@app.route("/reports", methods=["GET"])
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

        location = doc.get("location") or {}
        vision = doc.get("vision") or {}
        environment = doc.get("environment") or {}
        risk = doc.get("risk") or {}

        risk_level = (
            doc.get("risk_level")
            or risk.get("risk_level")
            or "LOW"
        )

        risk_score = (
            doc.get("risk_score")
            if doc.get("risk_score") is not None
            else risk.get("final_score")
        )

        status = doc.get("status") or "PENDING"

        reports.append({

            "id": doc_ref.id,

            "image": doc.get("image"),
            "image_url": doc.get("image_url", ""),

            "timestamp": doc.get("timestamp"),

            "email": doc.get("email"),
            "user_name": doc.get("user_name"),
            "priority": doc.get("priority"),

            "risk_level": risk_level,
            "risk_score": risk_score,

            "status": status,

            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "accuracy_m": location.get("accuracy_m"),

            "vision": vision,

            "environment": {
                "weather": {
                    "temperature_c": environment.get("temperature_c"),
                    "humidity_percent": environment.get("humidity_percent"),
                    "source": environment.get("source"),
                    "weather_timezone": environment.get("weather_timezone")
                },

                "rainfall": {
                    "24h_mm": environment.get("rainfall_24h_mm"),
                    "3d_mm": environment.get("rainfall_3d_mm"),
                    "7d_mm": environment.get("rainfall_7d_mm"),
                    "current_precipitation_mm":
                        environment.get("current_precipitation_mm")
                },

                "population": doc.get("population") or {},

                "nearby_facilities":
                    doc.get("nearby_facilities") or {},

                "historical_hotspot":
                    doc.get("historical_risk") or {}
            },

            "risk": {
                "breeding": {
                    "score": risk.get("biological_score"),
                    "level": risk_level
                },

                "municipal": {
                    "score": risk_score,
                    "level": risk_level,
                    "status": status
                }
            },

            "workflow": {
                "status": status,
                "display_flag": (
                    "GREEN"
                    if status == "COMPLETED"
                    else "YELLOW"
                    if status == "IN PROGRESS"
                    else "RED"
                )
            }
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