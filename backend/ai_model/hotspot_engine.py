import math
from datetime import datetime, timezone


class HotspotEngine:
    """
    LarvaeLens Historical Hotspot Engine V1.

    Firestore-backed implementation.

    Historical evidence is derived from previous LarvaeLens
    reports stored in the Firestore collection:

        larvae_reports

    The engine DOES NOT calculate risk.

    It only retrieves historical evidence around the
    current observation.

    Primary analysis radius:
        500 meters
    """

    ENGINE_VERSION = "historical-hotspot-engine-v1-firestore"

    DEFAULT_RADIUS_M = 500

    REPORT_COLLECTION = "larvae_reports"

    def __init__(
        self,
        radius_m=DEFAULT_RADIUS_M
    ):

        self.radius_m = radius_m

        print(
            "Historical Hotspot Engine V1 initialized."
        )

        print(
            "Database: Firestore"
        )


    # ========================================================
    # FIRESTORE
    # ========================================================

    def get_database(self):

        """
        Import the existing Firestore connection.

        This uses the same Firebase initialization that
        the rest of LarvaeLens already uses.
        """

        from database.firestore_config import db

        return db


    # ========================================================
    # HAVERSINE DISTANCE
    # ========================================================

    @staticmethod
    def calculate_distance_m(
        latitude1,
        longitude1,
        latitude2,
        longitude2
    ):

        earth_radius_m = 6371000.0

        lat1 = math.radians(
            float(latitude1)
        )

        lat2 = math.radians(
            float(latitude2)
        )

        delta_lat = math.radians(
            float(latitude2) -
            float(latitude1)
        )

        delta_lon = math.radians(
            float(longitude2) -
            float(longitude1)
        )

        a = (
            math.sin(
                delta_lat / 2
            ) ** 2
            +
            math.cos(lat1)
            *
            math.cos(lat2)
            *
            math.sin(
                delta_lon / 2
            ) ** 2
        )

        c = (
            2
            *
            math.atan2(
                math.sqrt(a),
                math.sqrt(1 - a)
            )
        )

        return (
            earth_radius_m * c
        )


    # ========================================================
    # SAFE FLOAT
    # ========================================================

    @staticmethod
    def safe_float(value):

        try:

            if value is None:
                return None

            return float(value)

        except (
            TypeError,
            ValueError
        ):

            return None


    # ========================================================
    # SAFE INT
    # ========================================================

    @staticmethod
    def safe_int(value):

        try:

            if value is None:
                return 0

            return int(value)

        except (
            TypeError,
            ValueError
        ):

            return 0


    # ========================================================
    # GET REPORT LOCATION
    # ========================================================

    @staticmethod
    def get_report_location(
        report
    ):

        """
        Current Firestore reports store coordinates inside:

            location.latitude
            location.longitude

        This also supports older documents where coordinates
        may have been stored at the top level.
        """

        location = (
            report.get("location")
            or {}
        )

        latitude = (
            location.get("latitude")
            if isinstance(
                location,
                dict
            )
            else None
        )

        longitude = (
            location.get("longitude")
            if isinstance(
                location,
                dict
            )
            else None
        )

        # Backwards compatibility

        if latitude is None:

            latitude = report.get(
                "latitude"
            )

        if longitude is None:

            longitude = report.get(
                "longitude"
            )

        latitude = (
            HotspotEngine.safe_float(
                latitude
            )
        )

        longitude = (
            HotspotEngine.safe_float(
                longitude
            )
        )

        return (
            latitude,
            longitude
        )


    # ========================================================
    # REPORT TIMESTAMP
    # ========================================================

    @staticmethod
    def get_report_year(
        report
    ):

        timestamp = report.get(
            "timestamp"
        )

        if timestamp is None:

            return None


        # Firestore Timestamp

        if hasattr(
            timestamp,
            "year"
        ):

            return int(
                timestamp.year
            )


        # Python datetime

        if isinstance(
            timestamp,
            datetime
        ):

            return int(
                timestamp.year
            )


        # ISO string

        try:

            text = str(
                timestamp
            ).strip()


            if not text:

                return None


            parsed =datetime.fromisoformat(
                text.replace("Z","+00:00")
                )


            return int(
                parsed.year
            )


        except Exception:

            return None


    # ========================================================
    # HISTORICAL EVIDENCE TEST
    # ========================================================

    @staticmethod
    def is_historical_evidence(
        report
    ):

        """
        Decide whether an old LarvaeLens report should
        contribute to historical hotspot evidence.

        We do NOT count every submitted report.

        A report qualifies when it has meaningful risk
        or biological evidence.
        """

        risk_level = str(
            report.get(
                "risk_level",
                ""
            )
        ).strip().upper()


        risk_score = (
            HotspotEngine.safe_float(
                report.get(
                    "risk_score"
                )
            )
        )


        vision = (
            report.get("vision")
            or {}
        )


        model4 = (
            vision.get("model4")
            or {}
        )


        larvae_count = (
            HotspotEngine.safe_int(
                model4.get(
                    "larvae_count"
                )
            )
        )


        biological_evidence = (
            str(
                vision.get(
                    "final_status",
                    ""
                )
            )
            .strip()
            .lower()
            ==
            "biological_evidence"
        )


        # Strongest evidence:
        # confirmed larvae

        if larvae_count > 0:

            return True


        if biological_evidence:

            return True


        # High / critical historical risk

        if risk_level in (
            "HIGH",
            "CRITICAL"
        ):

            return True


        if (
            risk_score is not None
            and risk_score >= 60
        ):

            return True


        return False


    # ========================================================
    # FETCH HISTORICAL REPORTS
    # ========================================================

    def fetch_historical_reports(
        self
    ):

        """
        Retrieve previous LarvaeLens reports
        from Firestore.

        We intentionally do not require a Firestore
        geospatial index because the collection stores
        coordinates inside nested maps.

        Distance filtering is performed locally using
        the Haversine calculation.
        """

        db = self.get_database()


        docs = (
            db.collection(
                self.REPORT_COLLECTION
            )
            .stream()
        )


        reports = []


        for document in docs:

            try:

                data = (
                    document.to_dict()
                    or {}
                )


                latitude, longitude = (
                    self.get_report_location(
                        data
                    )
                )


                if (
                    latitude is None
                    or
                    longitude is None
                ):

                    continue


                if not self.is_historical_evidence(
                    data
                ):

                    continue


                reports.append({

                    "id":
                        document.id,

                    "latitude":
                        latitude,

                    "longitude":
                        longitude,

                    "year":
                        self.get_report_year(
                            data
                        ),

                    "risk_level":
                        data.get(
                            "risk_level"
                        ),

                    "risk_score":
                        data.get(
                            "risk_score"
                        ),

                    "cases":
                        1,

                    "source":
                        "LarvaeLens Firestore reports",

                })


            except Exception as error:

                print(
                    "Skipping malformed "
                    "historical report:",
                    error
                )


        return reports


    # ========================================================
    # ANALYZE LOCATION
    # ========================================================

    def analyze(
        self,
        latitude,
        longitude
    ):

        """
        Find historical LarvaeLens reports
        within the configured radius.
        """

        # ----------------------------------------------------
        # GPS VALIDATION
        # ----------------------------------------------------

        latitude = (
            self.safe_float(
                latitude
            )
        )

        longitude = (
            self.safe_float(
                longitude
            )
        )


        if (
            latitude is None
            or
            longitude is None
        ):

            return {

                "hotspot_engine":
                    self.ENGINE_VERSION,

                "status":
                    "no_location",

                "search_radius_m":
                    self.radius_m,

                "hotspots_within_500m":
                    None,

                "nearest_hotspot_distance_m":
                    None,

                "historical_cases_within_500m":
                    None,

                "most_recent_hotspot_year":
                    None,

                "hotspots":
                    []

            }


        # ----------------------------------------------------
        # FIRESTORE
        # ----------------------------------------------------

        try:

            reports = (
                self.fetch_historical_reports()
            )


        except Exception as error:

            print(
                "Historical hotspot "
                "Firestore error:",
                error
            )


            return {

                "hotspot_engine":
                    self.ENGINE_VERSION,

                "status":
                    "database_unavailable",

                "search_radius_m":
                    self.radius_m,

                "hotspots_within_500m":
                    None,

                "nearest_hotspot_distance_m":
                    None,

                "historical_cases_within_500m":
                    None,

                "most_recent_hotspot_year":
                    None,

                "hotspots":
                    [],

                "error":
                    str(error)

            }


        # ----------------------------------------------------
        # DISTANCE FILTER
        # ----------------------------------------------------

        nearby_hotspots = []


        for report in reports:

            try:

                distance = (
                    self.calculate_distance_m(

                        latitude,

                        longitude,

                        report[
                            "latitude"
                        ],

                        report[
                            "longitude"
                        ]

                    )
                )


                if (
                    distance
                    <=
                    self.radius_m
                ):

                    result = (
                        report.copy()
                    )


                    result[
                        "distance_m"
                    ] = round(
                        distance,
                        2
                    )


                    nearby_hotspots.append(
                        result
                    )


            except Exception as error:

                print(
                    "Historical distance "
                    "calculation error:",
                    error
                )


        # ----------------------------------------------------
        # SORT
        # ----------------------------------------------------

        nearby_hotspots.sort(

            key=lambda item:
                item[
                    "distance_m"
                ]

        )


        # ----------------------------------------------------
        # NO HISTORICAL REPORTS
        # ----------------------------------------------------

        if not nearby_hotspots:

            return {

                "hotspot_engine":
                    self.ENGINE_VERSION,

                "status":
                    "no_hotspots_within_radius",

                "search_radius_m":
                    self.radius_m,

                "hotspots_within_500m":
                    0,

                "nearest_hotspot_distance_m":
                    None,

                "historical_cases_within_500m":
                    0,

                "most_recent_hotspot_year":
                    None,

                "hotspots":
                    [],

                "source":
                    "LarvaeLens Firestore reports"

            }


        # ----------------------------------------------------
        # NEAREST
        # ----------------------------------------------------

        nearest = (
            nearby_hotspots[0]
        )


        # ----------------------------------------------------
        # HISTORICAL CASES
        # ----------------------------------------------------

        historical_cases = sum(

            self.safe_int(
                item.get(
                    "cases",
                    1
                )
            )

            for item
            in nearby_hotspots

        )


        # ----------------------------------------------------
        # MOST RECENT YEAR
        # ----------------------------------------------------

        years = [

            item.get(
                "year"
            )

            for item
            in nearby_hotspots

            if item.get(
                "year"
            ) is not None

        ]


        most_recent_year = (

            max(years)

            if years

            else None

        )


        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        return {

            "hotspot_engine":
                self.ENGINE_VERSION,

            "status":
                "hotspots_found",

            "search_radius_m":
                self.radius_m,

            "hotspots_within_500m":
                len(
                    nearby_hotspots
                ),

            "nearest_hotspot_distance_m":
                nearest[
                    "distance_m"
                ],

            "historical_cases_within_500m":
                historical_cases,

            "most_recent_hotspot_year":
                most_recent_year,

            "hotspots":
                nearby_hotspots,

            "source":
                "LarvaeLens Firestore reports"

        }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    engine = HotspotEngine()


    print(
        "\n=============================================="
    )

    print(
        "HISTORICAL HOTSPOT ENGINE V1 - FIRESTORE"
    )

    print(
        "=============================================="
    )


    try:

        result = engine.analyze(

            latitude=22.8046,

            longitude=86.2029

        )


        print(
            "\nSTATUS:",
            result.get(
                "status"
            )
        )


        print(
            "Search radius:",
            result.get(
                "search_radius_m"
            ),
            "m"
        )


        print(
            "Historical reports within 500m:",
            result.get(
                "hotspots_within_500m"
            )
        )


        print(
            "Nearest historical report:",
            result.get(
                "nearest_hotspot_distance_m"
            ),
            "m"
        )


        print(
            "Historical cases:",
            result.get(
                "historical_cases_within_500m"
            )
        )


        print(
            "Most recent year:",
            result.get(
                "most_recent_hotspot_year"
            )
        )


    except Exception as error:

        print(
            "\nHotspot Engine test failed:"
        )

        print(error)


    print(
        "\n=============================================="
    )