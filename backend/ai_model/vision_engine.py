from pathlib import Path

from ultralytics import YOLO

from backend.ai_model.environmental_engine import EnvironmentalEngine


# ============================================================
# MODEL CONFIGURATION
# ============================================================

# Model 1:
# Breeding-object detection
MODEL1_PATH = (
    r"C:\Users\siddh\Desktop\Larvelens"
    r"\runs\detect\baseline-v1\weights\best.pt"
)

# Model 2:
# Water inside breeding-object segmentation/detection
MODEL2_PATH = (
    r"C:\Users\siddh\Desktop\Larvelens"
    r"\runs\segment\water-seg-v1\weights\best.pt"
)

# Model 3:
# Open stagnant-water habitat segmentation
MODEL3_PATH = (
    r"C:\Users\siddh\Documents\Codex\2026-08-11"
    r"\inspect-open-stagnant-water-zip-and"
    r"\runs\model3_balanced_v3\weights\best.pt"
)

# Model 4:
# Mosquito larvae detection
MODEL4_PATH = (
    r"C:\Users\siddh\Desktop\Larvelens"
    r"\runs\detect\model4-larvae-v1\weights\best.pt"
)


# ============================================================
# VISION ENGINE
# ============================================================

class VisionEngine:
    """
    LarvaeLens Vision Engine V1.

    ------------------------------------------------------------
    DECISION PIPELINE
    ------------------------------------------------------------

    IMAGE
       |
       v
    MODEL 1: Breeding object?
       |
       +---- YES ----> MODEL 2: Water inside object?
       |                    |
       |                    +---- YES ----> MODEL 4: Larvae?
       |                    |                    |
       |                    |                    +---- YES
       |                    |                    |     Biological Evidence
       |                    |                    |
       |                    |                    +---- NO
       |                    |                          Potential Breeding
       |                    |
       |                    +---- NO
       |                         Garbage
       |
       +---- NO -----> MODEL 3: Habitat?
                            |
                            +---- YES ----> MODEL 4: Larvae?
                            |                    |
                            |                    +---- YES
                            |                    |     Biological Evidence
                            |                    |
                            |                    +---- NO
                            |                          Potential Breeding
                            |
                            +---- NO
                                 Garbage


    ------------------------------------------------------------
    V1 EVIDENCE
    ------------------------------------------------------------

    Model 1:
        - detected objects
        - class
        - confidence
        - bounding box

    Model 2:
        - detected water type
        - confidence
        - bounding box

    Model 3:
        - habitat class
        - confidence
        - bounding box
        - bounding-box area
        - bounding-box image ratio
        - segmentation mask area
        - segmentation mask image ratio

    Model 4:
        - individual larvae
        - individual non-larvae
        - confidence
        - bounding boxes
        - larvae count
        - non-larvae count
        - habitat area
        - larvae density

    Environmental evidence:
        - GPS location
        - timestamp
        - temperature
        - humidity
        - rainfall
        - population
        - nearby facilities
        - historical hotspots


    IMPORTANT:
        Area values are IMAGE-SPACE PIXEL measurements.

        They are NOT:
            cm²
            m²
            larvae/m²

        Physical area requires camera calibration,
        depth information, a known reference object,
        or another scale-estimation method.
    """

    def __init__(self):

        self.engine_version = "vision-engine-v1"

        print("Initializing LarvaeLens Vision Engine V1...")

        # ----------------------------------------------------
        # ENVIRONMENTAL ENGINE
        # ----------------------------------------------------

        self.environmental_engine = EnvironmentalEngine()

        # ----------------------------------------------------
        # LOAD MODELS
        # ----------------------------------------------------

        self.model1 = YOLO(MODEL1_PATH)

        self.model2 = YOLO(MODEL2_PATH)

        self.model3 = YOLO(MODEL3_PATH)

        self.model4 = YOLO(MODEL4_PATH)

        print("Vision Engine V1 initialized.")

    # ========================================================
    # MAIN ANALYSIS PIPELINE
    # ========================================================

    def analyze(
        self,
        image_path,

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        latitude=None,
        longitude=None,
        accuracy_m=None,

        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        temperature_c=None,
        humidity_percent=None,

        # ----------------------------------------------------
        # RAINFALL
        # ----------------------------------------------------

        rainfall_24h_mm=None,
        rainfall_3d_mm=None,
        rainfall_7d_mm=None,

        # ----------------------------------------------------
        # POPULATION
        # ----------------------------------------------------

        estimated_population=None,
        population_density=None,

        # ----------------------------------------------------
        # NEARBY FACILITIES
        # ----------------------------------------------------

        schools_nearby=None,
        hospitals_nearby=None,
        colleges_nearby=None,

        # ----------------------------------------------------
        # HISTORICAL RISK
        # ----------------------------------------------------

        historical_hotspots=None,
        historical_cases=None,

        # ----------------------------------------------------
        # TIMESTAMP
        # ----------------------------------------------------

        timestamp=None,
    ):
        """
        Main Vision Engine V1 entry point.

        V1 performs:

            1. Image validation
            2. Environmental evidence collection
            3. Model 1
            4. Model 2 OR Model 3 routing
            5. Model 4 larvae detection
            6. Larvae density calculation where applicable
            7. Combined Vision + Environmental evidence result
        """

        image_path = Path(image_path)

        # ====================================================
        # IMAGE VALIDATION
        # ====================================================

        if not image_path.exists():

            return self._result(
                status="invalid_image",
                message="Image file does not exist.",
            )

        if not image_path.is_file():

            return self._result(
                status="invalid_image",
                message="Image path is not a file.",
            )

        # ====================================================
        # ENVIRONMENTAL EVIDENCE
        # ====================================================

        environment = self.environmental_engine.collect(

            latitude=latitude,

            longitude=longitude,

            accuracy_m=accuracy_m,

            temperature_c=temperature_c,

            humidity_percent=humidity_percent,

            rainfall_24h_mm=rainfall_24h_mm,

            rainfall_3d_mm=rainfall_3d_mm,

            rainfall_7d_mm=rainfall_7d_mm,

            estimated_population=estimated_population,

            population_density=population_density,

            schools_nearby=schools_nearby,

            hospitals_nearby=hospitals_nearby,

            colleges_nearby=colleges_nearby,

            historical_hotspots=historical_hotspots,

            historical_cases=historical_cases,

            timestamp=timestamp,
        )

        # ====================================================
        # MODEL 1
        # ====================================================

        model1 = self.run_model1(image_path)

        # ====================================================
        # MODEL 1 = YES
        #
        # Run Model 2.
        # ====================================================

        if model1["detected"]:

            model2 = self.run_model2(
                image_path,
                model1,
            )

            # =================================================
            # MODEL 2 = YES
            #
            # Object + water confirmed.
            # Run Model 4.
            # =================================================

            if model2["water_detected"]:

                # -------------------------------------------------
                # IMPORTANT:
                #
                # Container water does NOT use habitat area.
                #
                # Therefore:
                #
                # habitat_area_pixels = None
                #
                # We do NOT calculate larvae density for the
                # container route because Model 2 does not provide
                # a reliable physical/segmentation habitat area.
                # -------------------------------------------------

                model4 = self.run_model4(
                    image_path,
                    source="container_water",
                    habitat_area_pixels=None,
                )

                return self._build_final_result(

                    route="model1_model2",

                    model1=model1,

                    model2=model2,

                    model3=None,

                    model4=model4,

                    environment=environment,
                )

            # =================================================
            # MODEL 2 = NO
            #
            # Breeding object detected but water not confirmed.
            #
            # Stop pipeline.
            # =================================================

            return self._result(

                status="garbage",

                route="model1_model2_failed",

                model1=model1,

                model2=model2,

                model3=None,

                model4=None,

                environment=environment,
            )

        # ====================================================
        # MODEL 1 = NO
        #
        # Only now run Model 3.
        # ====================================================

        model3 = self.run_model3(image_path)

        # ====================================================
        # MODEL 3 = YES
        # ====================================================

        if model3["detected"]:

            # ------------------------------------------------
            # CALCULATE HABITAT AREA
            #
            # ONLY open_stagnant_water is used for larvae
            # density.
            # ------------------------------------------------

            habitat_area_pixels = 0.0

            for detection in model3["classes"]:

                if (
                    detection["class"]
                    == "open_stagnant_water"
                ):

                    habitat_area_pixels += (
                        detection["mask_area_pixels"]
                    )

            # ------------------------------------------------
            # If segmentation area is unavailable,
            # do not invent a value.
            # ------------------------------------------------

            if habitat_area_pixels <= 0:

                habitat_area_pixels = None

            # =================================================
            # MODEL 4
            # =================================================

            model4 = self.run_model4(

                image_path,

                source="open_stagnant_water",

                habitat_area_pixels=habitat_area_pixels,
            )

            return self._build_final_result(

                route="model3",

                model1=model1,

                model2=None,

                model3=model3,

                model4=model4,

                environment=environment,
            )

        # ====================================================
        # MODEL 3 = NO
        #
        # No required habitat evidence.
        # ====================================================

        return self._result(

            status="garbage",

            route="model3_failed",

            model1=model1,

            model2=None,

            model3=model3,

            model4=None,

            environment=environment,
        )

    # ========================================================
    # MODEL 1
    # ========================================================

    def run_model1(self, image_path):
        """
        Model 1:
        Breeding-object detector.

        Classes:

            0 -> Bottle
            1 -> Coconut-Exocarp
            2 -> Drain-Inlet
            3 -> Tire
            4 -> Vase
        """

        results = self.model1.predict(

            source=str(image_path),

            imgsz=640,

            conf=0.25,

            verbose=False,
        )

        objects = []

        confidences = []

        # ----------------------------------------------------
        # PROCESS DETECTIONS
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

                class_name = self.model1.names.get(

                    class_id,

                    "unknown",
                )

                bbox = [

                    float(value)

                    for value in box.xyxy[0].tolist()

                ]

                objects.append({

                    "class": class_name,

                    "confidence": confidence,

                    "bbox": bbox,

                })

                confidences.append(
                    confidence
                )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {

            "detected": (
                len(objects) > 0
            ),

            "objects": objects,

            "confidence": (

                max(confidences)

                if confidences

                else 0.0

            ),
        }

    # ========================================================
    # MODEL 2
    # ========================================================

    def run_model2(
        self,
        image_path,
        model1_result=None,
    ):
        """
        Model 2:
        Detect water inside a breeding object.

        Classes:

            0 -> tire_with_water
            1 -> vase_with_water

        model1_result is accepted so the method can later
        use Model 1 detections for spatial association.
        """

        results = self.model2.predict(

            source=str(image_path),

            imgsz=640,

            conf=0.25,

            verbose=False,
        )

        objects = []

        confidences = []

        # ----------------------------------------------------
        # PROCESS DETECTIONS
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

                class_name = self.model2.names.get(

                    class_id,

                    "unknown",
                )

                bbox = [

                    float(value)

                    for value in box.xyxy[0].tolist()

                ]

                objects.append({

                    "class": class_name,

                    "confidence": confidence,

                    "bbox": bbox,

                })

                confidences.append(
                    confidence
                )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {

            "water_detected": (
                len(objects) > 0
            ),

            "objects": objects,

            "confidence": (

                max(confidences)

                if confidences

                else 0.0

            ),
        }

    # ========================================================
    # MODEL 3
    # ========================================================

    @staticmethod
    def _polygon_area(polygon):
        """
        Calculate polygon area using the shoelace formula.

        The polygon coordinates are in the original image
        coordinate system supplied by Ultralytics.
        """

        if polygon is None:

            return 0.0

        if len(polygon) < 3:

            return 0.0

        x = polygon[:, 0]

        y = polygon[:, 1]

        area = 0.5 * abs(

            sum(

                + x[i] * y[(i + 1) % len(polygon)]
                - y[i] * x[(i + 1) % len(polygon)]

                for i in range(
                    len(polygon)
                )

            )

        )

        return float(area)

    def run_model3(self, image_path):
        """
        Model 3:
        Open stagnant-water habitat segmentation.

        Classes:

            0 -> open_stagnant_water
            1 -> water_in_container
            2 -> dense_vegetation_habitat

        For every detected object we preserve:

            - class
            - confidence
            - bbox
            - bbox_area_pixels
            - bbox_ratio
            - mask_area_pixels
            - mask_ratio
        """

        results = self.model3.predict(

            source=str(image_path),

            imgsz=640,

            conf=0.25,

            verbose=False,
        )

        detections = []

        confidences = []

        # ----------------------------------------------------
        # PROCESS RESULTS
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # PROCESS EACH DETECTION
            # ------------------------------------------------

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
                # CLASS NAME
                # --------------------------------------------

                class_name = self.model3.names.get(

                    class_id,

                    "unknown",
                )

                # --------------------------------------------
                # BOUNDING BOX
                # --------------------------------------------

                bbox = [

                    float(value)

                    for value in box.xyxy[0].tolist()

                ]

                x1, y1, x2, y2 = bbox

                bbox_width = max(

                    0.0,

                    x2 - x1,
                )

                bbox_height = max(

                    0.0,

                    y2 - y1,
                )

                bbox_area_pixels = (

                    bbox_width
                    * bbox_height

                )

                bbox_ratio = (

                    bbox_area_pixels
                    / image_area_pixels

                    if image_area_pixels > 0

                    else 0.0

                )

                # --------------------------------------------
                # SEGMENTATION MASK
                # --------------------------------------------

                mask_area_pixels = 0.0

                mask_ratio = 0.0

                if (

                    masks is not None

                    and index < len(masks.xy)

                ):

                    polygon = masks.xy[index]

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
                # SAVE DETECTION
                # --------------------------------------------

                detections.append({

                    "class": class_name,

                    "confidence": confidence,

                    "bbox": bbox,

                    "bbox_area_pixels": (

                        float(
                            bbox_area_pixels
                        )

                    ),

                    "bbox_ratio": (

                        float(
                            bbox_ratio
                        )

                    ),

                    "mask_area_pixels": (

                        float(
                            mask_area_pixels
                        )

                    ),

                    "mask_ratio": (

                        float(
                            mask_ratio
                        )

                    ),
                })

                confidences.append(
                    confidence
                )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {

            "detected": (

                len(detections) > 0

            ),

            "classes": detections,

            "confidence": (

                max(confidences)

                if confidences

                else 0.0

            ),
        }

    # ========================================================
    # MODEL 4
    # ========================================================

    def run_model4(
        self,
        image_path,
        source,
        habitat_area_pixels=None,
    ):
        """
        Model 4:
        Mosquito larvae detection.

        Classes:

            0 -> Bukan Jentik
            1 -> Jentik

        ----------------------------------------------------
        LARVAE DENSITY FORMULA
        ----------------------------------------------------

            D = (N / A) * 10000

        Where:

            D = larvae density per 10,000 pixels

            N = number of detected Jentik

            A = habitat segmentation area in pixels

        IMPORTANT:

            This is IMAGE-SPACE density.

            It is NOT larvae/m².

            Physical density requires physical image scale.
        """

        results = self.model4.predict(

            source=str(image_path),

            imgsz=640,

            conf=0.25,

            verbose=False,
        )

        larvae = []

        non_larvae = []

        larvae_confidences = []

        # ----------------------------------------------------
        # PROCESS DETECTIONS
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

                    for value in box.xyxy[0].tolist()

                ]

                # --------------------------------------------
                # CLASS 1 = JENTIK
                # --------------------------------------------

                if class_id == 1:

                    larvae.append({

                        "class": "Jentik",

                        "confidence": confidence,

                        "bbox": bbox,

                    })

                    larvae_confidences.append(
                        confidence
                    )

                # --------------------------------------------
                # CLASS 0 = BUKAN JENTIK
                # --------------------------------------------

                elif class_id == 0:

                    non_larvae.append({

                        "class": "Bukan Jentik",

                        "confidence": confidence,

                        "bbox": bbox,

                    })

        # ====================================================
        # COUNTS
        # ====================================================

        larvae_count = len(
            larvae
        )

        non_larvae_count = len(
            non_larvae
        )

        larvae_detected = (
            larvae_count > 0
        )

        # ====================================================
        # LARVAE DENSITY
        # ====================================================

        larvae_density_per_10000_pixels = None

        if (

            habitat_area_pixels is not None

            and habitat_area_pixels > 0

        ):

            larvae_density_per_10000_pixels = (

                larvae_count
                / float(
                    habitat_area_pixels
                )

            ) * 10000.0

        # ====================================================
        # RETURN
        # ====================================================

        return {

            "detected": (
                larvae_detected
            ),

            "larvae": larvae,

            "non_larvae": non_larvae,

            "confidence": (

                max(
                    larvae_confidences
                )

                if larvae_confidences

                else 0.0

            ),

            "larvae_count": (
                larvae_count
            ),

            "non_larvae_count": (
                non_larvae_count
            ),

            "habitat_area_pixels": (

                float(
                    habitat_area_pixels
                )

                if habitat_area_pixels is not None

                else None

            ),

            "larvae_density_per_10000_pixels": (

                larvae_density_per_10000_pixels

            ),

            "source": source,
        }

    # ========================================================
    # FINAL RESULT BUILDER
    # ========================================================

    def _build_final_result(
        self,
        route,
        model1,
        model2,
        model3,
        model4,
        environment=None,
    ):
        """
        Convert model evidence into the current V1 status.

        Biological evidence:
            At least one Jentik is detected.

        Potential breeding:
            Habitat/water evidence exists,
            but Jentik was not detected.
        """

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if (

            model4 is not None

            and model4["detected"]

        ):

            status = (
                "biological_evidence"
            )

        else:

            status = (
                "potential_breeding"
            )

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        return self._result(

            status=status,

            route=route,

            model1=model1,

            model2=model2,

            model3=model3,

            model4=model4,

            environment=environment,
        )

    # ========================================================
    # GENERIC RESULT
    # ========================================================

    def _result(
        self,
        status,
        message=None,
        **kwargs,
    ):
        """
        Create a standardized Vision Engine response.
        """

        result = {

            "engine": (
                self.engine_version
            ),

            "status": status,
        }

        if message is not None:

            result["message"] = (
                message
            )

        result.update(
            kwargs
        )

        return result


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    engine = VisionEngine()

    result = engine.analyze(
        "test_image.jpg"
    )

    print(
        "\n===== VISION ENGINE V1 RESULT ====="
    )

    print(result)