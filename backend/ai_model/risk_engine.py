"""
LarvaeLens Risk Engine V1

Two independent assessments:

1. Breeding Risk
   Answers:
   "How likely is this observation to represent a mosquito
    breeding site?"

2. Municipal Intervention Priority
   Answers:
   "Should the municipality prioritize resources for this location?"

This is a transparent rule-based V1 for competition/demo use.
It is NOT a trained machine-learning model.

The same features can later be used to train the research ML model.
"""

from typing import Any, Dict, Optional


class RiskEngine:
    """
    LarvaeLens Risk Engine V1.
    """

    VERSION = "risk-engine-v1"

    def __init__(self):
        print("Risk Engine V1 initialized.")

    # =========================================================
    # GENERAL HELPERS
    # =========================================================

    @staticmethod
    def _number(value, default=0.0):
        """
        Safely convert a value to float.
        """
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value, default=0):
        """
        Safely convert a value to int.
        """
        if value is None:
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_level(score: float) -> str:
        """
        Convert 0-100 score to risk category.
        """

        if score < 25:
            return "LOW"

        if score < 50:
            return "MODERATE"

        if score < 75:
            return "HIGH"

        return "CRITICAL"

    # =========================================================
    # RAINFALL SCORING
    # =========================================================

    def _rainfall_component(
        self,
        rainfall_24h,
        rainfall_3d,
        rainfall_7d
    ):
        """
        Rainfall contributes a maximum of 10 points.

        24h  -> max 5
        3d   -> max 3
        7d   -> max 2

        These are V1 engineering thresholds and should be
        validated/refined later using historical data.
        """

        r24 = None if rainfall_24h is None else self._number(rainfall_24h)
        r3 = None if rainfall_3d is None else self._number(rainfall_3d)
        r7 = None if rainfall_7d is None else self._number(rainfall_7d)

        # -----------------------------
        # 24 hour rainfall / 5
        # -----------------------------

        if r24 <= 0:
            score_24h = 0
        elif r24 < 5:
            score_24h = 1
        elif r24 < 10:
            score_24h = 3
        else:
            score_24h = 5

        # -----------------------------
        # 3 day rainfall / 3
        # -----------------------------

        if r3 <= 0:
            score_3d = 0
        elif r3 < 10:
            score_3d = 1
        elif r3 < 25:
            score_3d = 2
        else:
            score_3d = 3

        # -----------------------------
        # 7 day rainfall / 2
        # -----------------------------

        if r7 <= 0:
            score_7d = 0
        elif r7 < 25:
            score_7d = 1
        else:
            score_7d = 2

        available_scores = []

        if r24 is not None:
            available_scores.append(score_24h)

        if r3 is not None:
            available_scores.append(score_3d)

        if r7 is not None:
            available_scores.append(score_7d)

        if available_scores:
            total = sum(available_scores)
        else:
            total = None

        return {
            "score": total,
            "maximum": 10,
            "available": bool(available_scores),
            "rainfall_24h_mm": r24,
            "rainfall_3d_mm": r3,
            "rainfall_7d_mm": r7,
            "points": {
                "rainfall_24h": score_24h,
                "rainfall_3d": score_3d,
                "rainfall_7d": score_7d,
            }
        }

    # =========================================================
    # LARVAE PRESENCE
    # =========================================================

    def _larvae_presence_score(self, model4):
        detected = bool(
            model4.get("detected", False)
        )

        count = self._safe_int(
            model4.get("larvae_count", 0)
        )

        if detected or count > 0:
            return 20

        return 0

    # =========================================================
    # LARVAE COUNT
    # =========================================================

    def _larvae_count_score(self, model4):
        count = self._safe_int(
            model4.get("larvae_count", 0)
        )

        if count <= 0:
            return 0

        if count <= 2:
            return 4

        if count <= 5:
            return 8

        if count <= 10:
            return 12

        return 15

    # =========================================================
    # LARVAE DENSITY
    # =========================================================

    def _larvae_density_score(self, model4):
        density = self._number(
            model4.get(
                "larvae_density_per_10000_pixels",
                0
            )
        )

        if density <= 0:
            score = 0

        elif density <= 0.5:
            score = 3

        elif density <= 1.0:
            score = 6

        elif density <= 2.5:
            score = 9

        elif density <= 5.0:
            score = 12

        else:
            score = 15

        return {
            "score": score,
            "maximum": 15,
            "density_per_10000_pixels": density
        }

    # =========================================================
    # HABITAT TYPE
    # =========================================================

    def _habitat_score(self, model3):
        """
        Maximum = 15.

        Uses the strongest detected habitat class.
        """

        classes = model3.get("classes", [])

        best_score = 0
        best_class = None

        for detection in classes:

            class_name = str(
                detection.get("class", "")
            ).lower().strip()

            if (
                "open_stagnant_water"
                in class_name
            ):
                score = 15

            elif (
                "dense_vegetation"
                in class_name
                or "vegetation"
                in class_name
            ):
                score = 12

            elif (
                "derelict_container"
                in class_name
                or "container"
                in class_name
            ):
                score = 9

            elif class_name:
                score = 6

            else:
                score = 0

            if score > best_score:
                best_score = score
                best_class = class_name

        return {
            "score": best_score,
            "maximum": 15,
            "habitat_class": best_class
        }

    # =========================================================
    # HABITAT SEGMENTATION
    # =========================================================

    def _habitat_area_score(self, model3):
        """
        Uses segmentation mask_ratio.

        IMPORTANT:
        bbox_ratio is NOT scored because bounding-box coverage
        and segmentation coverage represent overlapping evidence.

        mask_ratio is the primary habitat-area feature.
        """

        classes = model3.get("classes", [])

        best_ratio = 0.0
        best_area = 0.0

        for detection in classes:

            ratio = self._number(
                detection.get(
                    "mask_ratio",
                    0
                )
            )

            area = self._number(
                detection.get(
                    "mask_area_pixels",
                    0
                )
            )

            if ratio > best_ratio:
                best_ratio = ratio
                best_area = area

        if best_ratio < 0.10:
            score = 0

        elif best_ratio < 0.25:
            score = 3

        elif best_ratio < 0.40:
            score = 6

        elif best_ratio < 0.60:
            score = 10

        else:
            score = 15

        return {
            "score": score,
            "maximum": 15,
            "mask_area_pixels": best_area,
            "mask_ratio": best_ratio,
            "coverage_percent": best_ratio * 100
        }

    # =========================================================
    # BREEDING OBJECT
    # =========================================================

    def _breeding_object_score(self, model1):
        """
        Maximum = 10.

        We score the strongest object only.
        """

        if not model1:
            return {
                "score": 0,
                "maximum": 10,
                "objects": []
            }

        objects = model1.get(
            "objects",
            []
        )

        if not objects:
            return {
                "score": 0,
                "maximum": 10,
                "objects": []
            }

        best_score = 0
        object_names = []

        for obj in objects:

            name = str(
                obj.get(
                    "class",
                    ""
                )
            ).lower().strip()

            object_names.append(name)

            if "tire" in name:
                score = 10

            elif (
                "waste" in name
                or "container" in name
                or "vase" in name
            ):
                score = 8

            elif name:
                score = 6

            else:
                score = 0

            best_score = max(
                best_score,
                score
            )

        return {
            "score": best_score,
            "maximum": 10,
            "objects": object_names
        }

    # =========================================================
    # POPULATION
    # =========================================================

    def _population_score(self, population):
        density = population.get(
            "population_density_500m"
        )

        if density is None:
            return {
                "score": None,
                "maximum": 15,
                "available": False,
                "population_density": None
            }

        density = self._number(
            density
        )

        if density < 500:
            score = 2

        elif density < 5000:
            score = 5

        elif density <= 25000:
            score = 10

        else:
            score = 15

        return {
            "score": score,
            "maximum": 15,
            "available": True,
            "population_density": density
        }

    # =========================================================
    # HISTORICAL HOTSPOTS
    # =========================================================

    def _historical_hotspot_score(
        self,
        historical
    ):
        count = historical.get(
            "hotspots_within_500m"
        )

        if count is None:
            return {
                "score": None,
                "maximum": 20,
                "available": False,
                "hotspots_within_500m": None
            }

        count = self._safe_int(
            count
        )

        if count == 0:
            score = 0

        elif count < 10:
            score = 8

        elif count <= 50:
            score = 14

        else:
            score = 20

        return {
            "score": score,
            "maximum": 20,
            "available": True,
            "hotspots_within_500m": count
        }

    # =========================================================
    # REPEATED REPORTS
    # =========================================================

    def _repeated_reports_score(
        self,
        historical
    ):
        """
        This feature will become active when the database
        provides repeated reports in the surrounding area.

        Expected field:
            repeated_reports_within_500m

        V1:
            1 report       = 0
            2-3            = 5
            4-9            = 10
            10+            = 15
        """

        reports = historical.get(
            "repeated_reports_within_500m"
        )

        if reports is None:
            return {
                "score": None,
                "maximum": 15,
                "available": False,
                "reports": None
            }

        reports = self._safe_int(
            reports
        )

        if reports <= 1:
            score = 0

        elif reports <= 3:
            score = 5

        elif reports <= 9:
            score = 10

        else:
            score = 15

        return {
            "score": score,
            "maximum": 15,
            "available": True,
            "reports": reports
        }

    # =========================================================
    # FACILITIES
    # =========================================================

    def _facility_score(
        self,
        facilities
    ):
        """
        Uses validated facilities within 500m.

        Maximum = 10.
        """

        total = 0

        for category in (
            "schools",
            "hospitals",
            "higher_education"
        ):

            data = facilities.get(
                category,
                {}
            )

            summary = data.get(
                "spatial_summary",
                {}
            )

            value = summary.get(
                "within_500m"
            )

            if value is not None:
                total += self._safe_int(
                    value
                )

        if total == 0:
            score = 0

        elif total <= 2:
            score = 2

        elif total <= 5:
            score = 5

        elif total <= 10:
            score = 8

        else:
            score = 10

        return {
            "score": score,
            "maximum": 10,
            "facility_count_500m": total
        }

    # =========================================================
    # HOTSPOT PROXIMITY
    # =========================================================

    def _hotspot_proximity_score(
        self,
        historical
    ):
        distance = historical.get(
            "nearest_hotspot_distance_m"
        )

        if distance is None:
            return {
                "score": None,
                "maximum": 5,
                "available": False,
                "distance_m": None
            }

        distance = self._number(
            distance
        )

        if distance <= 50:
            score = 5

        elif distance <= 100:
            score = 4

        elif distance <= 200:
            score = 3

        elif distance <= 400:
            score = 2

        else:
            score = 1

        return {
            "score": score,
            "maximum": 5,
            "available": True,
            "distance_m": distance
        }

    # =========================================================
    # BREEDING RISK
    # =========================================================

    def calculate_breeding_risk(
        self,
        result: Dict[str, Any]
    ):
        """
        Calculate Breeding Risk /100.
        """

        model1 = result.get(
            "model1"
        ) or {}

        model3 = result.get(
            "model3"
        ) or {}

        model4 = result.get(
            "model4"
        ) or {}

        environment = result.get(
            "environment"
        ) or {}

        weather = environment.get(
            "weather",
            {}
        )

        # -----------------------------------------
        # Individual components
        # -----------------------------------------

        larvae_presence = (
            self._larvae_presence_score(
                model4
            )
        )

        larvae_count = (
            self._larvae_count_score(
                model4
            )
        )

        density = (
            self._larvae_density_score(
                model4
            )
        )

        habitat = (
            self._habitat_score(
                model3
            )
        )

        habitat_area = (
            self._habitat_area_score(
                model3
            )
        )

        object_score = (
            self._breeding_object_score(
                model1
            )
        )

        rainfall = (
            self._rainfall_component(
                weather.get(
                    "rainfall_24h_mm"
                ),
                weather.get(
                    "rainfall_3d_mm"
                ),
                weather.get(
                    "rainfall_7d_mm"
                )
            )
        )

        raw_score = (
            larvae_presence
            + larvae_count
            + density["score"]
            + habitat["score"]
            + habitat_area["score"]
            + object_score["score"]
            + rainfall["score"]
        )

        raw_score = min(
            100,
            max(0, raw_score)
        )

        base_level = self._get_level(
            raw_score
        )

        # -----------------------------------------
        # Biological escalation rules
        # -----------------------------------------

        escalation_reasons = []

        habitat_class = (
            habitat.get(
                "habitat_class"
            ) or ""
        ).lower()

        mask_ratio = (
            habitat_area.get(
                "mask_ratio",
                0
            )
        )

        larvae_count_value = (
            self._safe_int(
                model4.get(
                    "larvae_count",
                    0
                )
            )
        )

        # Large open stagnant water
        if (
            "open_stagnant_water"
            in habitat_class
            and mask_ratio >= 0.40
        ):
            escalation_reasons.append(
                "Large open stagnant-water "
                "habitat detected "
                "(segmentation coverage >= 40%)."
            )

        # Confirmed larvae
        if larvae_count_value > 0:
            escalation_reasons.append(
                "Larvae detected."
            )

        # Strong larvae evidence
        density_value = density.get(
            "density_per_10000_pixels",
            0
        )

        if (
            larvae_count_value > 0
            and density_value > 2.5
            and mask_ratio >= 0.40
        ):
            escalation_reasons.append(
                "Strong biological evidence: "
                "larvae, high larvae density, "
                "and substantial habitat coverage."
            )

        final_level = base_level

        # Large suitable habitat cannot be below HIGH.
        if (
            "open_stagnant_water"
            in habitat_class
            and mask_ratio >= 0.40
        ):
            minimum_rank = 2  # HIGH

            current_rank = {
                "LOW": 0,
                "MODERATE": 1,
                "HIGH": 2,
                "CRITICAL": 3
            }[final_level]

            if current_rank < minimum_rank:
                final_level = "HIGH"

        # Strong biological evidence can reach CRITICAL.
        if (
            larvae_count_value > 0
            and density_value > 2.5
            and mask_ratio >= 0.60
        ):
            final_level = "CRITICAL"

        return {
            "score": raw_score,
            "level": final_level,
            "base_level": base_level,
            "maximum": 100,
            "components": {
                "larvae_presence": {
                    "score": larvae_presence,
                    "maximum": 20
                },
                "larvae_count": {
                    "score": larvae_count,
                    "maximum": 15,
                    "count": larvae_count_value
                },
                "larvae_density": density,
                "habitat_type": habitat,
                "habitat_area": habitat_area,
                "breeding_object": object_score,
                "rainfall": rainfall
            },
            "escalation_reasons": escalation_reasons
        }

    # =========================================================
    # MUNICIPAL PRIORITY
    # =========================================================

    def calculate_municipal_priority(
        self,
        result: Dict[str, Any],
        breeding_risk: Dict[str, Any]
    ):
        """
        Calculate Municipal Intervention Priority /100.
        """

        environment = result.get(
            "environment"
        ) or {}

        population = environment.get(
            "population",
            {}
        )

        facilities = environment.get(
            "nearby_facilities",
            {}
        )

        historical = environment.get(
            "historical_risk",
            {}
        )

        weather = environment.get(
            "weather",
            {}
        )

        # -----------------------------------------
        # Breeding contribution /25
        # -----------------------------------------

        breeding_score = self._number(
            breeding_risk.get(
                "score",
                0
            )
        )

        breeding_contribution = (
            breeding_score * 0.25
        )

        # -----------------------------------------
        # Population /15
        # -----------------------------------------

        population_component = (
            self._population_score(
                population
            )
        )

        # -----------------------------------------
        # Historical /20
        # -----------------------------------------

        historical_component = (
            self._historical_hotspot_score(
                historical
            )
        )

        # -----------------------------------------
        # Rainfall /10
        # -----------------------------------------

        rainfall_component = (
            self._rainfall_component(
                weather.get(
                    "rainfall_24h_mm"
                ),
                weather.get(
                    "rainfall_3d_mm"
                ),
                weather.get(
                    "rainfall_7d_mm"
                )
            )
        )

        # -----------------------------------------
        # Repeated reports /15
        # -----------------------------------------

        reports_component = (
            self._repeated_reports_score(
                historical
            )
        )

        # -----------------------------------------
        # Facilities /10
        # -----------------------------------------

        facility_component = (
            self._facility_score(
                facilities
            )
        )

        # -----------------------------------------
        # Hotspot proximity /5
        # -----------------------------------------

        proximity_component = (
            self._hotspot_proximity_score(
                historical
            )
        )

        # -----------------------------------------
        # Handle unavailable database features
        # -----------------------------------------
        
        unavailable_components = []
        
        available_score = (
            breeding_contribution
            + facility_component["score"]
        )

        available_maximum = (
            25
            + 10
        )
        if rainfall_component["score"] is not None:
            available_score += (
                rainfall_component["score"]
            )
            available_maximum += 10
        if not rainfall_component["available"]:
            unavailable_components.append("rainfall")
        if not population_component["available"]:
            unavailable_components.append(
                "population"
            )

        if not historical_component["available"]:
            unavailable_components.append(
                "historical_hotspots"
            )

        if not reports_component["available"]:
            unavailable_components.append(
                "repeated_reports"
            )

        if not proximity_component["available"]:
            unavailable_components.append(
                "hotspot_proximity"
            )

        # -----------------------------------------
        # If database evidence is missing, normalize
        # available evidence instead of pretending
        # missing evidence equals zero.
        # -----------------------------------------

        if population_component["score"] is not None:
            available_score += (
                population_component["score"]
            )
            available_maximum += 15

        if historical_component["score"] is not None:
            available_score += (
                historical_component["score"]
            )
            available_maximum += 20

        if reports_component["score"] is not None:
            available_score += (
                reports_component["score"]
            )
            available_maximum += 15

        if proximity_component["score"] is not None:
            available_score += (
                proximity_component["score"]
            )
            available_maximum += 5

        if available_maximum > 0:
           municipal_score = (
                available_score
                / available_maximum
            ) * 100
        else:
           municipal_score = 0

        total_maximum = 100

        evidence_completeness = (
            available_maximum
            / total_maximum
        ) * 100

        municipal_score = round(
            min(
                100,
                max(
                    0,
                    municipal_score
                )
            ),
            2
        )

        level = self._get_level(
            municipal_score
        )

        return {
    "score": municipal_score,
    "level": level,
    "maximum": 100,

    "evidence_completeness": round(
        evidence_completeness,
        1
    ),

    "normalized_from_available_evidence": (
        len(unavailable_components) > 0
    ),
            "unavailable_components":
                unavailable_components,
            "components": {
                "breeding_risk_contribution": {
                    "score": round(
                        breeding_contribution,
                        2
                    ),
                    "maximum": 25,
                    "source_score":
                        breeding_score
                },
                "population": population_component,
                "historical_hotspots":
                    historical_component,
                "rainfall":
                    rainfall_component,
                "repeated_reports":
                    reports_component,
                "sensitive_facilities":
                    facility_component,
                "hotspot_proximity":
                    proximity_component
            }
        }

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(
        self,
        result: Dict[str, Any]
    ):
        """
        Run both risk assessments.
        """

        breeding_risk = (
            self.calculate_breeding_risk(
                result
            )
        )

        municipal_priority = (
            self.calculate_municipal_priority(
                result,
                breeding_risk
            )
        )

        return {
            "risk_engine":
                self.VERSION,

            "status":
                "success",

            "breeding_risk":
                breeding_risk,

            "municipal_priority":
                municipal_priority
        }


# =============================================================
# HUMAN-READABLE SUMMARY
# =============================================================

def print_risk_summary(risk_result):
    """
    Print a clean terminal summary.
    """

    breeding = risk_result.get(
        "breeding_risk",
        {}
    )

    municipal = risk_result.get(
        "municipal_priority",
        {}
    )

    print(
        "\n=============================================="
    )

    print(
        "LARVAELENS RISK ENGINE V1"
    )

    print(
        "=============================================="
    )

    print("\nBREEDING RISK")

    print(
        "Score:",
        breeding.get("score"),
        "/ 100"
    )

    print(
        "Level:",
        breeding.get("level")
    )

    print("\nBREEDING RISK COMPONENTS")

    components = breeding.get(
        "components",
        {}
    )

    for name, data in components.items():

        if isinstance(data, dict):

            print(
                f"{name}:",
                data.get("score"),
                "/",
                data.get("maximum")
            )

    reasons = breeding.get(
        "escalation_reasons",
        []
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

    print(
        "\nMUNICIPAL INTERVENTION PRIORITY"
    )

    print(
        "Score:",
        municipal.get("score"),
        "/ 100"
    )

    print(
        "Level:",
        municipal.get("level")
    )

    unavailable = municipal.get(
        "unavailable_components",
        []
    )

    if unavailable:

        print(
            "\nDATABASE/CONTEXT NOT AVAILABLE"
        )

        for item in unavailable:
            print(
                "-",
                item
            )

    print(
        "\n=============================================="
    )


# =============================================================
# DIRECT TEST
# =============================================================

if __name__ == "__main__":

    print(
        "Risk Engine V1 standalone test."
    )

    print(
        "This engine expects the combined "
        "VisionEngine result dictionary."
    )

    print(
        "Use VisionEngine.analyze() and pass "
        "its result to RiskEngine.analyze()."
    )