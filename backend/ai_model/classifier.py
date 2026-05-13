import cv2
import numpy as np

def classify_risk(image_path):

    image = cv2.imread(image_path)

    # Resize image
    image = cv2.resize(image, (300,300))

    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Detect green/murky colors
    lower_green = np.array([25, 40, 40])
    upper_green = np.array([90, 255, 255])

    mask = cv2.inRange(hsv, lower_green, upper_green)

    green_pixels = np.sum(mask > 0)

    # Detect darkness
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    brightness = np.mean(gray)

    # Risk logic
    if green_pixels > 15000 and brightness < 100:
        return "HIGH"

    elif green_pixels > 7000:
        return "MEDIUM"

    else:
        return "LOW"