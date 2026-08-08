import cv2
import numpy as np

MODEL_VERSION = "rule-cv-v2"


def analyze_image(image_path):
    """Analyze a suspected mosquito-breeding image using the existing CV rules.

    This keeps the original rule-based classifier intact while exposing the
    visual evidence and a normalized risk score for the competition pipeline.
    The score is a breeding-site visual risk score, not a disease prediction.
    """
    image = cv2.imread(image_path)

    if image is None:
        return {
            "risk_level": "LOW",
            "risk_score": 0,
            "analysis_method": "rule_based_cv",
            "model_version": MODEL_VERSION,
            "evidence": ["Image could not be analyzed"],
            "metrics": {},
        }

    image = cv2.resize(image, (300, 300))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Green / dirty-water visual signal
    lower_green = np.array([25, 30, 30])
    upper_green = np.array([95, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    green_pixels = int(np.sum(green_mask > 0))

    # Blue / reflection visual signal
    lower_blue = np.array([80, 30, 30])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_pixels = int(np.sum(blue_mask > 0))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    edges = cv2.Canny(gray, 100, 200)
    edge_pixels = int(np.sum(edges > 0))

    # Kept as an exposed metric for future model development.
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Preserve the original classification boundaries.
    high_signal = (
        green_pixels > 18000
        and brightness < 120
        and edge_pixels > 4000
    )

    medium_signal = (
        green_pixels > 9000
        or blue_pixels > 12000
        or brightness < 140
    )

    # Convert the existing rule evidence into an interpretable 0-100 score.
    score = 0
    evidence = []

    if green_pixels > 18000:
        score += 35
        evidence.append("Strong green/murky-water visual signal")
    elif green_pixels > 9000:
        score += 20
        evidence.append("Moderate green/murky-water visual signal")

    if blue_pixels > 12000:
        score += 15
        evidence.append("Strong water/reflection visual signal")
    elif blue_pixels > 6000:
        score += 7
        evidence.append("Moderate water/reflection visual signal")

    if brightness < 120:
        score += 20
        evidence.append("Low scene brightness")
    elif brightness < 140:
        score += 10
        evidence.append("Moderately low scene brightness")

    if edge_pixels > 4000:
        score += 15
        evidence.append("High visual texture/edge density")
    elif edge_pixels > 2500:
        score += 7
        evidence.append("Moderate visual texture/edge density")

    if blur_score < 80:
        score += 5
        evidence.append("Low image texture variation")

    score = min(score, 100)

    if high_signal:
        risk_level = "HIGH"
    elif medium_signal:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if not evidence:
        evidence.append("No strong visual breeding-site signals detected")

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "analysis_method": "rule_based_cv",
        "model_version": MODEL_VERSION,
        "evidence": evidence,
        "metrics": {
            "green_pixels": green_pixels,
            "blue_pixels": blue_pixels,
            "brightness": round(brightness, 2),
            "edge_pixels": edge_pixels,
            "blur_score": round(blur_score, 2),
        },
    }


def classify_risk(image_path):
    """Backward-compatible API used by the existing application."""
    return analyze_image(image_path)["risk_level"]
