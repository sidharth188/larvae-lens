from pathlib import Path
from ultralytics import YOLO


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL1_PATH = (
    r"C:\Users\siddh\Desktop\Larvelens"
    r"\runs\detect\baseline-v1\weights\best.pt"
)

MODEL2_PATH = (
    r"C:\Users\siddh\Desktop\Larvelens"
    r"\runs\segment\water-seg-v1\weights\best.pt"
)

MODEL3_PATH = (
    r"C:\Users\siddh\Documents\Codex\2026-08-11"
    r"\inspect-open-stagnant-water-zip-and"
    r"\runs\model3_balanced_v3\weights\best.pt"
)
MODEL4_PATH = r"C:\Users\siddh\Desktop\Larvelens\runs\detect\model4-larvae-v1\weights\best.pt"


class VisionEngine:
    """
    Vision Engine V0

    LOCKED DECISION FLOW:

    IMAGE
      |
      v
    MODEL 1: Breeding object?
      |
      +---- YES ----> MODEL 2: Water inside object?
      |                  |
      |                  +---- YES ----> MODEL 4: Larvae?
      |                  |                    |
      |                  |                    +---- YES --> Biological Evidence
      |                  |                    |
      |                  |                    +---- NO  --> Potential Breeding
      |                  |
      |                  +---- NO ----> GARBAGE
      |
      +---- NO -----> MODEL 3: Open stagnant water?
                             |
                             +---- YES ----> MODEL 4: Larvae?
                             |                    |
                             |                    +---- YES --> Biological Evidence
                             |                    |
                             |                    +---- NO  --> Potential Breeding
                             |
                             +---- NO ----> GARBAGE
    """

    def __init__(self):

        self.engine_version = "vision-engine-v0"

        # Load Model 1
        self.model1 = YOLO(MODEL1_PATH)

        # Load Model 2
        self.model2 = YOLO(MODEL2_PATH)

        # Load Model 3
        self.model3 = YOLO(MODEL3_PATH)

        # Load Model 4
        self.model4 = YOLO(MODEL4_PATH)

    # ========================================================
    # MAIN ANALYSIS PIPELINE
    # ========================================================

    def analyze(self, image_path):
        """
        Main entry point for Vision Engine V0.

        Decision logic:

        Model 1 = YES
            -> Model 2
                -> YES -> Model 4
                -> NO  -> Garbage

        Model 1 = NO
            -> Model 3
                -> YES -> Model 4
                -> NO  -> Garbage
        """

        image_path = Path(image_path)

        # ----------------------------------------------------
        # IMAGE VALIDATION
        # ----------------------------------------------------

        if not image_path.exists():

            return self._result(
                status="invalid_image",
                message="Image file does not exist."
            )

        # ====================================================
        # MODEL 1
        # ====================================================

        model1 = self.run_model1(image_path)

        # ====================================================
        # MODEL 1 = YES
        #
        # IMPORTANT:
        # If Model 1 detects a breeding object,
        # ONLY Model 2 is checked.
        #
        # Model 3 MUST NOT be called if Model 2 fails.
        # ====================================================

        if model1["detected"]:

            model2 = self.run_model2(
                image_path,
                model1
            )

            # ------------------------------------------------
            # MODEL 2 = YES
            #
            # Object + water confirmed.
            # Go to Model 4.
            # ------------------------------------------------

            if model2["water_detected"]:

                model4 = self.run_model4(
                    image_path,
                    source="container_water"
                )

                return self._build_final_result(
                    route="model1_model2",
                    model1=model1,
                    model2=model2,
                    model3=None,
                    model4=model4
                )

            # ------------------------------------------------
            # MODEL 2 = NO
            #
            # STOP.
            #
            # Do NOT run Model 3.
            #
            # This image is garbage for this pipeline.
            # ------------------------------------------------

            return self._result(
                status="garbage",
                route="model1_model2_failed",
                model1=model1,
                model2=model2,
                model3=None,
                model4=None
            )

        # ====================================================
        # MODEL 1 = NO
        #
        # Only now do we check Model 3.
        # ====================================================

        model3 = self.run_model3(image_path)

        # ----------------------------------------------------
        # MODEL 3 = YES
        #
        # Open stagnant water detected.
        # Go to Model 4.
        # ----------------------------------------------------

        if model3["detected"]:

            model4 = self.run_model4(
                image_path,
                source="open_stagnant_water"
            )

            return self._build_final_result(
                route="model3",
                model1=model1,
                model2=None,
                model3=model3,
                model4=model4
            )

        # ----------------------------------------------------
        # MODEL 3 = NO
        #
        # No required habitat evidence.
        # ----------------------------------------------------

        return self._result(
            status="garbage",
            route="model3_failed",
            model1=model1,
            model2=None,
            model3=model3,
            model4=None
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
            verbose=False
        )

        detected_objects = []
        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            for cls, conf in zip(
                result.boxes.cls.tolist(),
                result.boxes.conf.tolist()
            ):

                class_id = int(cls)
                confidence = float(conf)

                class_name = self.model1.names.get(
                    class_id,
                    "unknown"
                )

                detected_objects.append(class_name)
                confidences.append(confidence)

        detected = len(detected_objects) > 0

        return {
            "detected": detected,
            "objects": detected_objects,
            "confidence": (
                max(confidences)
                if confidences
                else 0.0
            )
        }

    # ========================================================
    # MODEL 2
    # ========================================================

    def run_model2(self, image_path, model1_result):
        """
        Model 2:
        Detect water inside a breeding object.

        Classes:
            0 -> tire_with_water
            1 -> vase_with_water
        """

        results = self.model2.predict(
            source=str(image_path),
            imgsz=640,
            conf=0.25,
            verbose=False
        )

        detected_objects = []
        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            for cls, conf in zip(
                result.boxes.cls.tolist(),
                result.boxes.conf.tolist()
            ):

                class_id = int(cls)
                confidence = float(conf)

                class_name = self.model2.names.get(
                    class_id,
                    "unknown"
                )

                detected_objects.append(class_name)
                confidences.append(confidence)

        water_detected = len(detected_objects) > 0

        return {
            "water_detected": water_detected,
            "objects": detected_objects,
            "confidence": (
                max(confidences)
                if confidences
                else 0.0
            )
        }

    # ========================================================
    # MODEL 3
    # ========================================================

    def run_model3(self, image_path):
        """
        Model 3:
        Open stagnant-water segmentation.

        Classes:
            0 -> open_stagnant_water
            1 -> water_in_container
            2 -> dense_vegetation_habitat
        """

        results = self.model3.predict(
            source=str(image_path),
            imgsz=640,
            conf=0.25,
            verbose=False
        )

        detected_classes = []
        confidences = []

        for result in results:

            if result.boxes is None:
                continue

            for cls, conf in zip(
                result.boxes.cls.tolist(),
                result.boxes.conf.tolist()
            ):

                class_id = int(cls)
                confidence = float(conf)

                if class_id == 0:

                    class_name = "open_stagnant_water"

                elif class_id == 1:

                    class_name = "water_in_container"

                elif class_id == 2:

                    class_name = "dense_vegetation_habitat"

                else:

                    class_name = "unknown"

                detected_classes.append(class_name)
                confidences.append(confidence)

        detected = len(detected_classes) > 0

        return {
            "detected": detected,
            "classes": detected_classes,
            "confidence": (
                max(confidences)
                if confidences
                else 0.0
            )
        }

    # ========================================================
    # MODEL 4
    # ========================================================

    def run_model4(self, image_path, source):
       """
       Model 4:
       Mosquito larvae detection.

       Classes:
        0: Bukan Jentik
        1: Jentik

       Only class 1 (Jentik) counts as biological evidence.
       """

       results = self.model4.predict(
           source=str(image_path),
           imgsz=640,
           conf=0.25,
           verbose=False
       )

       larvae_confidences = []
       bukan_jentik_confidences = []

       for result in results:

           if result.boxes is None:
               continue

           for cls, conf in zip(
            result.boxes.cls.tolist(),
            result.boxes.conf.tolist()
           ):
            class_id = int(cls)
            confidence = float(conf)

            if class_id == 1:
                # Jentik = mosquito larvae
                larvae_confidences.append(confidence)

            elif class_id == 0:
                # Bukan Jentik = not mosquito larvae
                bukan_jentik_confidences.append(confidence)

    # Biological evidence exists only when
    # at least one Jentik detection is found.
       larvae_detected = len(larvae_confidences) > 0

       return {
           "detected": larvae_detected,

           "confidence": (
               max(larvae_confidences)
               if larvae_confidences
               else 0.0
           ),

           "larvae_count": len(larvae_confidences),

           "non_larvae_count": len(
               bukan_jentik_confidences
           ),

           "source": source
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
        model4
    ):

        # ----------------------------------------------------
        # MODEL 4 = YES
        # ----------------------------------------------------

        if model4 and model4["detected"]:

            return self._result(
                status="biological_evidence",
                route=route,
                model1=model1,
                model2=model2,
                model3=model3,
                model4=model4
            )

        # ----------------------------------------------------
        # HABITAT FOUND
        # BUT LARVAE NOT DETECTED
        # ----------------------------------------------------

        return self._result(
            status="potential_breeding",
            route=route,
            model1=model1,
            model2=model2,
            model3=model3,
            model4=model4
        )

    # ========================================================
    # GENERIC RESULT
    # ========================================================

    def _result(
        self,
        status,
        message=None,
        **kwargs
    ):

        result = {
            "engine": self.engine_version,
            "status": status
        }

        if message:

            result["message"] = message

        result.update(kwargs)

        return result


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    engine = VisionEngine()

    result = engine.analyze(
        "test_image.jpg"
    )

    print("\n===== VISION ENGINE RESULT =====")
    print(result)