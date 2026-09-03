"""
LarvaeLens Vision Engine V1

Pipeline:

IMAGE
  |
  +--> Model 1: Breeding Object
  |       |
  |       +--> Model 2: Water in Object
  |               |
  |               +--> Model 4: Larvae
  |
  +--> Model 3: Habitat
          |
          +--> Model 4: Larvae
  |
  +--> Environmental Engine
          |
          +--> Weather
          +--> Population
          +--> Nearby Facilities
          +--> Historical Hotspots
  |
  +--> Risk Engine
          |
          +--> Breeding Risk
          +--> Municipal Priority


Model paths are loaded from .env.

IMPORTANT:
Model 3 area measurements are IMAGE-SPACE PIXEL measurements.
They are not physical m² measurements.
"""

from pathlib import Path
import os


# ============================================================
# LOAD ENVIRONMENT FIRST
# ============================================================

from dotenv import load_dotenv


# Project root:
#
# backend/ai_model/vision_engine.py
#          ^
#          |
# parents[0] = ai_model
# parents[1] = backend
# parents[2] = project root
#
BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    BASE_DIR / ".env"
)


# ============================================================
# THIRD-PARTY
# ============================================================

from ultralytics import YOLO


# ============================================================
# LARVAELENS ENGINES
# ============================================================

from ai_model.environmental_engine import EnvironmentalEngine
from ai_model.risk_engine import RiskEngine


# ============================================================
# MODEL PATH CONFIGURATION
# ============================================================

MODEL1_PATH = os.getenv(
    "MODEL1_PATH", "/app/models/model1_detect.pt"
)

MODEL2_PATH = os.getenv(
    "MODEL2_PATH", "/app/models/model2_segment.pt"
)

MODEL3_PATH = os.getenv(
    "MODEL3_PATH", "/app/models/model3_segment.pt"
)

MODEL4_PATH = os.getenv(
    "MODEL4_PATH", "/app/models/model4_detect.pt"
)


# ============================================================
# MODEL PATH VALIDATION
# ============================================================

def validate_model_path(
    name,
    path
):
    """
    Validate a model path loaded from .env.
    """

    if not path:

        raise RuntimeError(
            f"{name} is not configured in .env"
        )

    model_path = Path(
        path
    ).expanduser()

    if not model_path.exists():

        raise FileNotFoundError(
            f"{name} does not exist:\n"
            f"{model_path}"
        )

    if not model_path.is_file():

        raise FileNotFoundError(
            f"{name} is not a file:\n"
            f"{model_path}"
        )

    return str(
        model_path
    )


# ============================================================
# VISION ENGINE
# ============================================================

class VisionEngine:

    def __init__(self):

        self.engine_version = (
            "vision-engine-v1"
        )

        print(
            "Initializing LarvaeLens Vision Engine V1..."
        )

        # ----------------------------------------------------
        # ENVIRONMENTAL ENGINE
        # ----------------------------------------------------

        self.environmental_engine = (
            EnvironmentalEngine()
        )

        # ----------------------------------------------------
        # RISK ENGINE
        # ----------------------------------------------------

        self.risk_engine = (
            RiskEngine()
        )

        # ----------------------------------------------------
        # VALIDATE MODEL PATHS
        # ----------------------------------------------------

        model1_path = validate_model_path(
            "MODEL1_PATH",
            MODEL1_PATH
        )

        model2_path = validate_model_path(
            "MODEL2_PATH",
            MODEL2_PATH
        )

        model3_path = validate_model_path(
            "MODEL3_PATH",
            MODEL3_PATH
        )

        model4_path = validate_model_path(
            "MODEL4_PATH",
            MODEL4_PATH
        )

        # ----------------------------------------------------
        # LOAD MODELS
        # ----------------------------------------------------

        self.model1 = YOLO(
            model1_path
        )

        self.model2 = YOLO(
            model2_path
        )

        self.model3 = YOLO(
            model3_path
        )

        self.model4 = YOLO(
            model4_path
        )

        print(
            "Vision Engine V1 initialized."
        )

    # ========================================================
    # MAIN ANALYSIS
    # ========================================================

    def analyze(
        self,
        image_path,
        latitude=None,
        longitude=None,
        accuracy_m=None,

        temperature_c=None,
        humidity_percent=None,

        rainfall_24h_mm=None,
        rainfall_3d_mm=None,
        rainfall_7d_mm=None,

        estimated_population=None,
        population_density=None,

        schools_nearby=None,
        hospitals_nearby=None,
        colleges_nearby=None,

        historical_hotspots=None,
        historical_cases=None,

        timestamp=None,
    ):
        """
        Complete Vision + Environment + Risk analysis.
        """

        image_path = Path(
            image_path
        )

        # ====================================================
        # IMAGE VALIDATION
        # ====================================================

        if not image_path.exists():

            return self._result(
                status="invalid_image",
                message=(
                    "Image file does not exist."
                )
            )

        if not image_path.is_file():

            return self._result(
                status="invalid_image",
                message=(
                    "Image path is not a file."
                )
            )

        # ====================================================
        # ENVIRONMENT
        # ====================================================

        try:

            environment = (
                self.environmental_engine.collect(
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_m=accuracy_m,

                    temperature_c=temperature_c,
                    humidity_percent=humidity_percent,

                    rainfall_24h_mm=(
                        rainfall_24h_mm
                    ),

                    rainfall_3d_mm=(
                        rainfall_3d_mm
                    ),

                    rainfall_7d_mm=(
                        rainfall_7d_mm
                    ),

                    estimated_population=(
                        estimated_population
                    ),

                    population_density=(
                        population_density
                    ),

                    schools_nearby=(
                        schools_nearby
                    ),

                    hospitals_nearby=(
                        hospitals_nearby
                    ),

                    colleges_nearby=(
                        colleges_nearby
                    ),

                    historical_hotspots=(
                        historical_hotspots
                    ),

                    historical_cases=(
                        historical_cases
                    ),

                    timestamp=timestamp,
                )
            )

        except Exception as error:

            print(
                "Environmental Engine error:",
                error
            )

            environment = {

                "status":
                    "error",

                "error":
                    str(error),

                "location": {

                    "latitude":
                        latitude,

                    "longitude":
                        longitude,

                    "accuracy_m":
                        accuracy_m,
                },

                "weather": {

                    "temperature_c":
                        temperature_c,

                    "humidity_percent":
                        humidity_percent,

                    "rainfall_24h_mm":
                        rainfall_24h_mm,

                    "rainfall_3d_mm":
                        rainfall_3d_mm,

                    "rainfall_7d_mm":
                        rainfall_7d_mm,
                },

                "population": {},

                "nearby_facilities": {},

                "historical_risk": {},
            }

        # ====================================================
        # MODEL 1
        # ====================================================

        model1 = self.run_model1(
            image_path
        )

        # ====================================================
        # MODEL 1 DETECTED
        # ====================================================

        if model1["detected"]:

            model2 = self.run_model2(
                image_path,
                model1
            )

            # ------------------------------------------------
            # MODEL 2 FOUND WATER
            # ------------------------------------------------

            if model2["water_detected"]:

                model4 = self.run_model4(
                    image_path,

                    source="container_water",

                    habitat_area_pixels=None
                )

                return self._complete_result(
                    route="model1_model2",

                    model1=model1,
                    model2=model2,
                    model3=None,
                    model4=model4,

                    environment=environment
                )

            # ------------------------------------------------
            # MODEL 2 DID NOT FIND WATER
            # ------------------------------------------------

            return self._complete_result(

                route="model1_model2_failed",

                model1=model1,
                model2=model2,
                model3=None,
                model4=None,

                environment=environment,

                forced_status="garbage"
            )

        # ====================================================
        # MODEL 1 NOT DETECTED
        #
        # RUN MODEL 3
        # ====================================================

        model3 = self.run_model3(
            image_path
        )

        # ====================================================
        # MODEL 3 DETECTED HABITAT
        # ====================================================

        if model3["detected"]:

            # ------------------------------------------------
            # VALIDATE MODEL 3 HABITAT EVIDENCE
            #
            # Do not accept every Model 3 detection.
            # A noisy / irrelevant image may produce a
            # low-confidence false positive.
            # ------------------------------------------------

            VALID_HABITAT_CLASSES = {
               "open_stagnant_water",
               "water_in_container",
               "dense_vegetation_habitat",
            }

            MIN_HABITAT_CONFIDENCE = 0.35
            MIN_HABITAT_MASK_RATIO = 0.005
            MAX_HABITAT_MASK_RATIO = 0.90

            valid_habitats = []

            for detection in model3.get("classes", []):

                class_name = detection.get("class")

                confidence = float(
                    detection.get("confidence", 0.0)
                )

                mask_ratio = float(
                    detection.get("mask_ratio", 0.0)
                )

                bbox_ratio = float(
                     detection.get("bbox_ratio", 0.0)
                )

                valid_class = (
                    class_name in VALID_HABITAT_CLASSES
                )

                valid_confidence = (
                    confidence >= MIN_HABITAT_CONFIDENCE
                )

                valid_mask = (
                    MIN_HABITAT_MASK_RATIO
                    <= mask_ratio
                    <= MAX_HABITAT_MASK_RATIO
                )

                # Reject detections that unrealistically cover
                # almost the entire image. These are commonly
                # produced by noisy / irrelevant images.
                full_image_false_positive = (
                    mask_ratio > 0.90
                    or bbox_ratio > 0.98
                )

                if (
                    valid_class
                    and valid_confidence
                    and valid_mask
                    and not full_image_false_positive
                ):
                    valid_habitats.append(detection)

                else:
                    print(
                        "Model 3 detection rejected:",
                        {
                            "class": class_name,
                            "confidence": round(confidence, 3),
                            "mask_ratio": round(mask_ratio, 3),
                            "bbox_ratio": round(bbox_ratio, 3),
                        }
                    )
            # ------------------------------------------------
            # NO VALID HABITAT EVIDENCE
            # ------------------------------------------------

            if not valid_habitats:

                print(
                    "Model 3 rejected: "
                    "no valid habitat evidence."
                )

                return self._complete_result(
                    route="model3_invalid",
                    model1=model1,
                    model2=None,
                    model3=model3,
                    model4=None,
                    environment=environment,
                    forced_status="garbage"
                )

            # ------------------------------------------------
            # Find largest VALID habitat mask.
            # ------------------------------------------------

            habitat_area_pixels = 0.0

            for detection in valid_habitats:

                if (
                    detection.get("class")
                    in VALID_HABITAT_CLASSES
                ):

                    habitat_area_pixels = max(
                        habitat_area_pixels,
                        float(
                            detection.get(
                                "mask_area_pixels",
                                0.0
                            )
                        )
                    )

            if habitat_area_pixels <= 0:
                habitat_area_pixels = None

            # ------------------------------------------------
            # MODEL 4
            # ------------------------------------------------

            model4 = self.run_model4(
                image_path,
                source="open_stagnant_water",
                habitat_area_pixels=(
                    habitat_area_pixels
                )
            )

            return self._complete_result(
                route="model3",
                model1=model1,
                model2=None,
                model3=model3,
                model4=model4,
                environment=environment
            )
        # ====================================================
        # NO HABITAT
        # ====================================================

        return self._complete_result(

            route="model3_failed",

            model1=model1,

            model2=None,

            model3=model3,

            model4=None,

            environment=environment,

            forced_status="garbage"
        )

    # ========================================================
    # MODEL 1
    # ========================================================

    def run_model1(
        self,
        image_path
    ):
        """
        Breeding-object detector.
        """

        results = self.model1.predict(

            source=str(
                image_path
            ),

            imgsz=640,

            conf=0.25,

            verbose=False
        )

        objects = []

        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(
                    box.cls.item()
                )

                confidence = float(
                    box.conf.item()
                )

                class_name = (
                    self.model1.names.get(
                        class_id,
                        "unknown"
                    )
                )

                bbox = [
                    float(value)

                    for value in (
                        box.xyxy[0].tolist()
                    )
                ]

                objects.append({

                    "class":
                        class_name,

                    "confidence":
                        confidence,

                    "bbox":
                        bbox
                })

                confidences.append(
                    confidence
                )

        return {

            "detected":
                len(objects) > 0,

            "objects":
                objects,

            "confidence":
                max(confidences)
                if confidences
                else 0.0
        }

    # ========================================================
    # MODEL 2
    # ========================================================

    def run_model2(
        self,
        image_path,
        model1_result=None
    ):
        """
        Water-inside-object detector.
        """

        results = self.model2.predict(

            source=str(
                image_path
            ),

            imgsz=640,

            conf=0.25,

            verbose=False
        )

        objects = []

        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(
                    box.cls.item()
                )

                confidence = float(
                    box.conf.item()
                )

                class_name = (
                    self.model2.names.get(
                        class_id,
                        "unknown"
                    )
                )

                bbox = [
                    float(value)

                    for value in (
                        box.xyxy[0].tolist()
                    )
                ]

                objects.append({

                    "class":
                        class_name,

                    "confidence":
                        confidence,

                    "bbox":
                        bbox
                })

                confidences.append(
                    confidence
                )

        return {

            "water_detected":
                len(objects) > 0,

            "objects":
                objects,

            "confidence":
                max(confidences)
                if confidences
                else 0.0
        }

    # ========================================================
    # POLYGON AREA
    # ========================================================

    @staticmethod
    def _polygon_area(
        polygon
    ):
        """
        Calculate polygon area using the shoelace formula.
        """

        if polygon is None:
            return 0.0

        if len(polygon) < 3:
            return 0.0

        x = polygon[:, 0]

        y = polygon[:, 1]

        area = 0.5 * abs(

            sum(

                x[i]
                * y[
                    (i + 1)
                    % len(polygon)
                ]

                -

                y[i]
                * x[
                    (i + 1)
                    % len(polygon)
                ]

                for i in range(
                    len(polygon)
                )
            )
        )

        return float(
            area
        )

    # ========================================================
    # MODEL 3
    # ========================================================

    def run_model3(
        self,
        image_path
    ):
        """
        Habitat detection + segmentation.

        Every detection returns:

            class
            confidence
            bbox

            bbox_area_pixels
            bbox_ratio

            mask_area_pixels
            mask_ratio
        """

        results = self.model3.predict(

            source=str(
                image_path
            ),

            imgsz=640,

            conf=0.25,

            verbose=False
        )

        detections = []

        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            image_height, image_width = (
                result.orig_shape
            )

            image_area_pixels = float(

                image_height
                * image_width
            )

            masks = result.masks

            for index, box in enumerate(
                result.boxes
            ):

                class_id = int(
                    box.cls.item()
                )

                confidence = float(
                    box.conf.item()
                )

                # --------------------------------------------
                # CLASS MAPPING
                # --------------------------------------------

                if class_id == 0:

                    class_name = (
                        "open_stagnant_water"
                    )

                elif class_id == 1:

                    class_name = (
                        "water_in_container"
                    )

                elif class_id == 2:

                    class_name = (
                        "dense_vegetation_habitat"
                    )

                else:

                    class_name = "unknown"

                # --------------------------------------------
                # BOUNDING BOX
                # --------------------------------------------

                bbox = [
                    float(value)

                    for value in (
                        box.xyxy[0].tolist()
                    )
                ]

                x1, y1, x2, y2 = (
                    bbox
                )

                bbox_width = max(
                    0.0,
                    x2 - x1
                )

                bbox_height = max(
                    0.0,
                    y2 - y1
                )

                bbox_area_pixels = (

                    bbox_width
                    * bbox_height
                )

                if image_area_pixels > 0:

                    bbox_ratio = (

                        bbox_area_pixels
                        / image_area_pixels
                    )

                else:

                    bbox_ratio = 0.0

                # --------------------------------------------
                # SEGMENTATION
                # --------------------------------------------

                mask_area_pixels = 0.0

                mask_ratio = 0.0

                if (

                    masks is not None

                    and index
                    < len(masks.xy)
                ):

                    polygon = (
                        masks.xy[index]
                    )

                    mask_area_pixels = (
                        self._polygon_area(
                            polygon
                        )
                    )

                    if image_area_pixels > 0:

                        mask_ratio = (

                            mask_area_pixels
                            / image_area_pixels
                        )

                # --------------------------------------------
                # STORE DETECTION
                # --------------------------------------------

                detections.append({

                    "class":
                        class_name,

                    "confidence":
                        confidence,

                    "bbox":
                        bbox,

                    "bbox_area_pixels":
                        float(
                            bbox_area_pixels
                        ),

                    "bbox_ratio":
                        float(
                            bbox_ratio
                        ),

                    "mask_area_pixels":
                        float(
                            mask_area_pixels
                        ),

                    "mask_ratio":
                        float(
                            mask_ratio
                        )
                })

                confidences.append(
                    confidence
                )

        return {

            "detected":
                len(detections) > 0,

            "classes":
                detections,

            "confidence":
                max(confidences)
                if confidences
                else 0.0
        }

    # ========================================================
    # MODEL 4
    # ========================================================

    def run_model4(
        self,
        image_path,
        source,
        habitat_area_pixels=None
    ):
        """
        Larvae detector.

        Class 0 = Bukan Jentik
        Class 1 = Jentik

        Larvae density:

            larvae_count
            ---------------- * 10000
            habitat_area_pixels
        """

        results = self.model4.predict(

            source=str(
                image_path
            ),

            imgsz=640,

            conf=0.25,

            verbose=False
        )

        larvae = []

        non_larvae = []

        larvae_confidences = []

        non_larvae_confidences = []

        # ----------------------------------------------------
        # DETECTIONS
        # ----------------------------------------------------

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(
                    box.cls.item()
                )

                confidence = float(
                    box.conf.item()
                )

                bbox = [
                    float(value)

                    for value in (
                        box.xyxy[0].tolist()
                    )
                ]

                # --------------------------------------------
                # LARVAE
                # --------------------------------------------

                if class_id == 1:

                    larvae.append({

                        "class":
                            "Jentik",

                        "confidence":
                            confidence,

                        "bbox":
                            bbox
                    })

                    larvae_confidences.append(
                        confidence
                    )

                # --------------------------------------------
                # NON-LARVAE
                # --------------------------------------------

                elif class_id == 0:

                    non_larvae.append({

                        "class":
                            "Bukan Jentik",

                        "confidence":
                            confidence,

                        "bbox":
                            bbox
                    })

                    non_larvae_confidences.append(
                        confidence
                    )

        # ----------------------------------------------------
        # COUNTS
        # ----------------------------------------------------

        larvae_count = len(
            larvae
        )

        non_larvae_count = len(
            non_larvae
        )

        larvae_detected = (
            larvae_count > 0
        )

        # ----------------------------------------------------
        # LARVAE DENSITY
        # ----------------------------------------------------

        larvae_density = None

        if (

            habitat_area_pixels
            is not None

            and habitat_area_pixels > 0
        ):

            larvae_density = (

                larvae_count
                / float(
                    habitat_area_pixels
                )

                * 10000.0
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        return {

            "detected":
                larvae_detected,

            "larvae":
                larvae,

            "non_larvae":
                non_larvae,

            "confidence":
                max(
                    larvae_confidences
                )
                if larvae_confidences
                else 0.0,

            "larvae_count":
                larvae_count,

            "non_larvae_count":
                non_larvae_count,

            "habitat_area_pixels":
                (
                    float(
                        habitat_area_pixels
                    )

                    if habitat_area_pixels
                    is not None

                    else None
                ),

            "larvae_density_per_10000_pixels":
                larvae_density,

            "source":
                source
        }

    # ========================================================
    # COMPLETE RESULT
    # ========================================================

    def _complete_result(
        self,
        route,
        model1,
        model2,
        model3,
        model4,
        environment,
        forced_status=None
    ):
        """
        Build final result and run Risk Engine.
        """

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if forced_status is not None:

            status = (
                forced_status
            )

        elif (

            model4 is not None

            and model4.get(
                "detected",
                False
            )
        ):

            status = (
                "biological_evidence"
            )

        else:

            status = (
                "potential_breeding"
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = self._result(

            status=status,

            route=route,

            model1=model1,

            model2=model2,

            model3=model3,

            model4=model4,

            environment=environment
        )

        # ----------------------------------------------------
        # RISK ENGINE
        # ----------------------------------------------------

        if status != "garbage":

            try:

                risk_assessment = (
                    self.risk_engine.analyze(
                        result
                    )
                )

                result[
                    "risk_assessment"
                ] = risk_assessment

            except Exception as error:

                print(
                    "Risk Engine error:",
                    error
                )

                result[
                    "risk_assessment"
                ] = {

                    "risk_engine":
                        "risk-engine-v1",

                    "status":
                        "error",

                    "error":
                        str(error)
                }

        else:

            result[
                "risk_assessment"
            ] = {

                "risk_engine":
                    "risk-engine-v1",

                "status":
                    "not_applicable",

                "reason":
                    (
                        "No valid breeding "
                        "or habitat evidence."
                    )
            }

        return result

    # ========================================================
    # RESULT HELPER
    # ========================================================

    def _result(
        self,
        status,
        message=None,
        **kwargs
    ):
        """
        Standardized result object.
        """

        result = {

            "engine":
                self.engine_version,

            "status":
                status
        }

        if message:

            result[
                "message"
            ] = message

        result.update(
            kwargs
        )

        return result


# ================================================================
# HUMAN-READABLE SUMMARY
# ================================================================

def print_vision_summary(
    result
):
    """
    Print concise Vision + Environmental + Risk summary.
    """

    print(
        "\n=============================================="
    )

    print(
        "LARVAELENS VISION ENGINE V1"
    )

    print(
        "=============================================="
    )

    # ============================================================
    # STATUS
    # ============================================================

    print(
        "\nSTATUS"
    )

    print(
        "Status:",
        result.get(
            "status"
        )
    )

    print(
        "Route :",
        result.get(
            "route"
        )
    )

    # ============================================================
    # MODEL 1
    # ============================================================

    model1 = (
        result.get(
            "model1"
        )
        or {}
    )

    print(
        "\nMODEL 1 - BREEDING OBJECT"
    )

    print(
        "Detected:",
        model1.get(
            "detected",
            False
        )
    )

    print(
        "Confidence:",
        model1.get(
            "confidence",
            0.0
        )
    )

    for obj in model1.get(
        "objects",
        []
    ):

        print(
            " -",
            obj.get(
                "class"
            ),
            "| confidence:",
            round(
                obj.get(
                    "confidence",
                    0
                ),
                4
            )
        )

    # ============================================================
    # MODEL 2
    # ============================================================

    model2 = (
        result.get(
            "model2"
        )
        or {}
    )

    if model2:

        print(
            "\nMODEL 2 - WATER IN OBJECT"
        )

        print(
            "Water detected:",
            model2.get(
                "water_detected",
                False
            )
        )

        print(
            "Confidence:",
            model2.get(
                "confidence",
                0.0
            )
        )

        for obj in model2.get(
            "objects",
            []
        ):

            print(
                " -",
                obj.get(
                    "class"
                ),
                "| confidence:",
                round(
                    obj.get(
                        "confidence",
                        0
                    ),
                    4
                )
            )

    # ============================================================
    # MODEL 3
    # ============================================================

    model3 = (
        result.get(
            "model3"
        )
        or {}
    )

    if model3:

        print(
            "\nMODEL 3 - HABITAT"
        )

        print(
            "Detected:",
            model3.get(
                "detected",
                False
            )
        )

        print(
            "Confidence:",
            model3.get(
                "confidence",
                0.0
            )
        )

        for detection in model3.get(
            "classes",
            []
        ):

            print(
                " -",
                detection.get(
                    "class"
                ),
                "| confidence:",
                round(
                    detection.get(
                        "confidence",
                        0
                    ),
                    4
                )
            )

            bbox_area = detection.get(
                "bbox_area_pixels"
            )

            bbox_ratio = detection.get(
                "bbox_ratio"
            )

            mask_area = detection.get(
                "mask_area_pixels"
            )

            mask_ratio = detection.get(
                "mask_ratio"
            )

            print(
                "   Bounding-box area:",
                (
                    round(
                        bbox_area,
                        2
                    )
                    if bbox_area is not None
                    else None
                ),
                "pixels"
            )

            print(
                "   Bounding-box ratio:",
                (
                    round(
                        bbox_ratio,
                        6
                    )
                    if bbox_ratio is not None
                    else None
                )
            )

            print(
                "   Bounding-box coverage:",
                (
                    round(
                        bbox_ratio * 100,
                        2
                    )
                    if bbox_ratio is not None
                    else None
                ),
                "%"
            )

            print(
                "   Segmentation area:",
                (
                    round(
                        mask_area,
                        2
                    )
                    if mask_area is not None
                    else None
                ),
                "pixels"
            )

            print(
                "   Mask ratio:",
                (
                    round(
                        mask_ratio,
                        6
                    )
                    if mask_ratio is not None
                    else None
                )
            )

            print(
                "   Segmentation coverage:",
                (
                    round(
                        mask_ratio * 100,
                        2
                    )
                    if mask_ratio is not None
                    else None
                ),
                "%"
            )

    # ============================================================
    # MODEL 4
    # ============================================================

    model4 = (
        result.get(
            "model4"
        )
        or {}
    )

    if model4:

        print(
            "\nMODEL 4 - LARVAE"
        )

        print(
            "Larvae detected:",
            model4.get(
                "detected",
                False
            )
        )

        print(
            "Larvae count:",
            model4.get(
                "larvae_count",
                0
            )
        )

        print(
            "Non-larvae count:",
            model4.get(
                "non_larvae_count",
                0
            )
        )

        print(
            "Confidence:",
            model4.get(
                "confidence",
                0.0
            )
        )

        print(
            "Larvae density:",
            model4.get(
                "larvae_density_per_10000_pixels"
            ),
            "/ 10,000 pixels"
        )

        print(
            "Source:",
            model4.get(
                "source"
            )
        )

    # ============================================================
    # ENVIRONMENT
    # ============================================================

    environment = (
        result.get(
            "environment"
        )
        or {}
    )

    location = (
        environment.get(
            "location"
        )
        or {}
    )

    weather = (
        environment.get(
            "weather"
        )
        or {}
    )

    print(
        "\nENVIRONMENT"
    )

    print(
        "Latitude:",
        location.get(
            "latitude"
        )
    )

    print(
        "Longitude:",
        location.get(
            "longitude"
        )
    )

    print(
        "GPS accuracy:",
        location.get(
            "accuracy_m"
        ),
        "m"
    )

    print(
        "Temperature:",
        weather.get(
            "temperature_c"
        ),
        "°C"
    )

    print(
        "Humidity:",
        weather.get(
            "humidity_percent"
        ),
        "%"
    )

    print(
        "Rainfall 24h:",
        weather.get(
            "rainfall_24h_mm"
        ),
        "mm"
    )

    print(
        "Rainfall 3d:",
        weather.get(
            "rainfall_3d_mm"
        ),
        "mm"
    )

    print(
        "Rainfall 7d:",
        weather.get(
            "rainfall_7d_mm"
        ),
        "mm"
    )

    # ============================================================
    # POPULATION
    # ============================================================

    population = (
        environment.get(
            "population"
        )
        or {}
    )

    print(
        "\nPOPULATION"
    )

    print(
        "Estimated population 500m:",
        population.get(
            "estimated_population_500m",
            population.get(
                "estimated_population"
            )
        )
    )

    print(
        "Population density:",
        population.get(
            "population_density_500m",
            population.get(
                "population_density"
            )
        ),
        "people/km²"
    )

    # ============================================================
    # FACILITIES
    # ============================================================

    facilities = (
        environment.get(
            "nearby_facilities"
        )
        or {}
    )

    schools = (
        facilities.get(
            "schools"
        )
        or {}
    )

    hospitals = (
        facilities.get(
            "hospitals"
        )
        or {}
    )

    higher = (
        facilities.get(
            "higher_education"
        )
        or {}
    )

    schools_summary = (
        schools.get(
            "spatial_summary"
        )
        or {}
    )

    hospitals_summary = (
        hospitals.get(
            "spatial_summary"
        )
        or {}
    )

    higher_summary = (
        higher.get(
            "spatial_summary"
        )
        or {}
    )

    print(
        "\nNEARBY FACILITIES"
    )

    print(
        "Schools within 500m:",
        schools_summary.get(
            "within_500m"
        )
    )

    print(
        "Hospitals within 500m:",
        hospitals_summary.get(
            "within_500m"
        )
    )

    print(
        "Higher education within 500m:",
        higher_summary.get(
            "within_500m"
        )
    )

    # ============================================================
    # HISTORICAL HOTSPOT
    # ============================================================

    historical = (
        environment.get(
            "historical_risk"
        )
        or {}
    )

    print(
        "\nHISTORICAL HOTSPOT"
    )

    print(
        "Status:",
        historical.get(
            "status"
        )
    )

    print(
        "Search radius:",
        historical.get(
            "search_radius_m",
            500
        ),
        "m"
    )

    print(
        "Hotspots within 500m:",
        historical.get(
            "hotspots_within_500m"
        )
    )

    print(
        "Nearest hotspot:",
        historical.get(
            "nearest_hotspot_distance_m"
        ),
        "m"
    )

    print(
        "Historical cases:",
        historical.get(
            "historical_cases_within_500m"
        )
    )

    # ============================================================
    # RISK
    # ============================================================

    risk = (
        result.get(
            "risk_assessment"
        )
        or {}
    )

    if risk:

        print(
            "\n=============================================="
        )

        print(
            "RISK ASSESSMENT"
        )

        print(
            "=============================================="
        )

        # --------------------------------------------------------
        # BREEDING RISK
        # --------------------------------------------------------

        breeding = (
            risk.get(
                "breeding_risk"
            )
            or {}
        )

        print(
            "\nBREEDING RISK"
        )

        print(
            "Score:",
            breeding.get(
                "score"
            ),
            "/ 100"
        )

        print(
            "Level:",
            breeding.get(
                "level"
            )
        )

        # --------------------------------------------------------
        # COMPONENTS
        # --------------------------------------------------------

        components = (
            breeding.get(
                "components"
            )
            or {}
        )

        print(
            "\nBREEDING RISK COMPONENTS"
        )

        for name, data in components.items():

            if not isinstance(
                data,
                dict
            ):
                continue

            score = data.get(
                "score"
            )

            maximum = data.get(
                "maximum"
            )

            if score is not None:

                print(
                    f"{name}:",
                    score,
                    "/",
                    maximum
                )

        # --------------------------------------------------------
        # ESCALATION
        # --------------------------------------------------------

        reasons = (
            breeding.get(
                "escalation_reasons"
            )
            or []
        )

        if reasons:

            print(
                "\nBIOLOGICAL ESCALATION"
            )

            for reason in reasons:

                print(
                    "-",
                    reason
                )

        # --------------------------------------------------------
        # MUNICIPAL PRIORITY
        # --------------------------------------------------------

        municipal = (
            risk.get(
                "municipal_priority"
            )
            or {}
        )

        print(
            "\nMUNICIPAL INTERVENTION PRIORITY"
        )

        print(
            "Score:",
            municipal.get(
                "score"
            ),
            "/ 100"
        )

        print(
            "Level:",
            municipal.get(
                "level"
            )
        )

        if municipal.get(
            "normalized_from_available_evidence",
            False
        ):

            print(
                "Status: PROVISIONAL"
            )

            unavailable = (
                municipal.get(
                    "unavailable_components",
                    []
                )
            )

            if unavailable:

                print(
                    "Unavailable:",
                    ", ".join(
                        unavailable
                    )
                )

    print(
        "\n=============================================="
    )


# ================================================================
# DIRECT TEST
# ================================================================

if __name__ == "__main__":

    engine = VisionEngine()

    test_image = (
        r"C:\Users\siddh\Documents\Codex\2026-08-11"
        r"\inspect-open-stagnant-water-zip-and"
        r"\outputs\model3_balanced\test\images"
        r"\unit_0634__image173.jpeg"
    )

    result = engine.analyze(

        test_image,

        latitude=22.8046,

        longitude=86.2029,

        accuracy_m=8.5
    )

    print_vision_summary(
        result
    )