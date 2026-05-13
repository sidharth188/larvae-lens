import cv2
import numpy as np

def classify_risk(image_path):

    # Read image
    image = cv2.imread(image_path)

    if image is None:
        return "LOW"

    # Resize for consistency
    image = cv2.resize(image, (400, 400))

    # -----------------------------
    # HSV COLOR ANALYSIS
    # -----------------------------

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Green / dirty water detection
    lower_green = np.array([25, 30, 30])
    upper_green = np.array([95, 255, 255])

    green_mask = cv2.inRange(
        hsv,
        lower_green,
        upper_green
    )

    green_pixels = np.sum(green_mask > 0)

    # -----------------------------
    # WATER REFLECTION DETECTION
    # -----------------------------

    lower_blue = np.array([80, 30, 30])
    upper_blue = np.array([140, 255, 255])

    blue_mask = cv2.inRange(
        hsv,
        lower_blue,
        upper_blue
    )

    blue_pixels = np.sum(blue_mask > 0)

    # -----------------------------
    # DARKNESS / STAGNATION
    # -----------------------------

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    brightness = np.mean(gray)

    # -----------------------------
    # EDGE DENSITY
    # Helps detect textured stagnant areas
    # -----------------------------

    edges = cv2.Canny(
        gray,
        100,
        200
    )

    edge_pixels = np.sum(edges > 0)

    # -----------------------------
    # BLUR DETECTION
    # Stagnant water often has low texture
    # -----------------------------

    blur_score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    # -----------------------------
    # FINAL RISK LOGIC
    # -----------------------------

    if (

        green_pixels > 18000

        and

        brightness < 120

        and

        edge_pixels > 4000

    ):

        return "HIGH"

    elif (

        green_pixels > 9000

        or

        blue_pixels > 12000

        or

        brightness < 140

    ):

        return "MEDIUM"

    else:

        return "LOW"