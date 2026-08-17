import os
import math
from datetime import datetime, timezone

try:
    import psycopg2
except ImportError:
    psycopg2 = None


class HotspotEngine:
    """
    LarvaeLens Historical Hotspot Engine V1.

    Queries the LarvaeLens historical hotspot database
    and determines historical epidemiological evidence
    within a specified radius of an observation.

    Primary LarvaeLens analysis radius:
        500 meters

    IMPORTANT:
        This engine DOES NOT calculate risk.

        It only retrieves historical evidence.

    V1 spatial calculation:
        Haversine distance

    Future:
        PostgreSQL + PostGIS spatial queries.
    """

    ENGINE_VERSION = "historical-hotspot-engine-v1"

    DEFAULT_RADIUS_M = 500

    def __init__(
        self,
        radius_m=DEFAULT_RADIUS_M
    ):
        self.radius_m = radius_m

        # ----------------------------------------------------
        # DATABASE CONFIGURATION
        # ----------------------------------------------------

        self.database_url = os.getenv(
            "LARVAELENS_DATABASE_URL"
        )

        self.db_host = os.getenv(
            "LARVAELENS_DB_HOST"
        )

        self.db_port = os.getenv(
            "LARVAELENS_DB_PORT",
            "5432"
        )

        self.db_name = os.getenv(
            "LARVAELENS_DB_NAME"
        )

        self.db_user = os.getenv(
            "LARVAELENS_DB_USER"
        )

        self.db_password = os.getenv(
            "LARVAELENS_DB_PASSWORD"
        )

        print(
            "Historical Hotspot Engine V1 initialized."
        )

        if self.database_url:
            print(
                "Database: configured via "
                "LARVAELENS_DATABASE_URL"
            )

        elif (
            self.db_host
            and self.db_name
            and self.db_user
        ):
            print(
                "Database: PostgreSQL configuration detected."
            )

        else:
            print(
                "Database: NOT configured."
            )

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    def connect(self):
        """
        Create a PostgreSQL connection.
        """

        if psycopg2 is None:

            raise RuntimeError(
                "psycopg2 is not installed. "
                "Install it with: "
                "pip install psycopg2-binary"
            )

        if self.database_url:

            return psycopg2.connect(
                self.database_url,
                connect_timeout=10
            )

        if (
            not self.db_host
            or not self.db_name
            or not self.db_user
        ):

            raise RuntimeError(
                "PostgreSQL database is not configured."
            )

        return psycopg2.connect(

            host=self.db_host,

            port=self.db_port,

            dbname=self.db_name,

            user=self.db_user,

            password=self.db_password,

            connect_timeout=10
        )

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
        """
        Calculate great-circle distance between two
        geographic coordinates.

        Returns:
            distance in meters.
        """

        earth_radius_m = 6371000.0

        lat1 = math.radians(
            latitude1
        )

        lat2 = math.radians(
            latitude2
        )

        delta_lat = math.radians(
            latitude2 - latitude1
        )

        delta_lon = math.radians(
            longitude2 - longitude1
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
    # CREATE DATABASE TABLE
    # ========================================================

    def create_table(self):
        """
        Create the historical_hotspots table.

        This does not insert any data.
        """

        connection = self.connect()

        try:

            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                historical_hotspots (

                    id BIGSERIAL PRIMARY KEY,

                    latitude DOUBLE PRECISION NOT NULL,

                    longitude DOUBLE PRECISION NOT NULL,

                    year INTEGER,

                    month INTEGER,

                    cases INTEGER DEFAULT 0,

                    severity TEXT,

                    source TEXT,

                    created_at TIMESTAMPTZ
                        DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            connection.commit()

            cursor.close()

            print(
                "historical_hotspots table ready."
            )

        finally:

            connection.close()

    # ========================================================
    # FETCH HOTSPOTS
    # ========================================================

    def fetch_hotspots(self):
        """
        Retrieve historical hotspot records.

        No fake data is created.
        """

        connection = self.connect()

        try:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    latitude,
                    longitude,
                    year,
                    month,
                    cases,
                    severity,
                    source,
                    created_at
                FROM historical_hotspots
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                """
            )

            rows = cursor.fetchall()

            cursor.close()

            hotspots = []

            for row in rows:

                hotspots.append({

                    "id": row[0],

                    "latitude": float(
                        row[1]
                    ),

                    "longitude": float(
                        row[2]
                    ),

                    "year": row[3],

                    "month": row[4],

                    "cases": (
                        row[5]
                        if row[5] is not None
                        else 0
                    ),

                    "severity": row[6],

                    "source": row[7],

                    "created_at": (
                        row[8].isoformat()
                        if row[8]
                        else None
                    )
                })

            return hotspots

        finally:

            connection.close()

    # ========================================================
    # ANALYZE LOCATION
    # ========================================================

    def analyze(
        self,
        latitude,
        longitude
    ):
        """
        Find historical hotspots within the configured
        radius of the observation.

        Returns:

            hotspots_within_radius
            nearest hotspot
            nearest distance
            historical cases
            most recent hotspot year
        """

        # ----------------------------------------------------
        # GPS VALIDATION
        # ----------------------------------------------------

        if (
            latitude is None
            or longitude is None
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
        # DATABASE
        # ----------------------------------------------------

        try:

            hotspots = (
                self.fetch_hotspots()
            )

        except Exception as error:

            print(
                "Historical hotspot database error:",
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

        for hotspot in hotspots:

            distance = (
                self.calculate_distance_m(

                    latitude,

                    longitude,

                    hotspot[
                        "latitude"
                    ],

                    hotspot[
                        "longitude"
                    ]
                )
            )

            if (
                distance
                <=
                self.radius_m
            ):

                hotspot_result = (
                    hotspot.copy()
                )

                hotspot_result[
                    "distance_m"
                ] = round(
                    distance,
                    2
                )

                nearby_hotspots.append(
                    hotspot_result
                )

        # ----------------------------------------------------
        # SORT BY DISTANCE
        # ----------------------------------------------------

        nearby_hotspots.sort(

            key=lambda hotspot:
                hotspot[
                    "distance_m"
                ]
        )

        # ----------------------------------------------------
        # NO HOTSPOTS
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
                    []
            }

        # ----------------------------------------------------
        # NEAREST
        # ----------------------------------------------------

        nearest = nearby_hotspots[0]

        # ----------------------------------------------------
        # HISTORICAL CASES
        # ----------------------------------------------------

        historical_cases = sum(

            hotspot.get(
                "cases",
                0
            )

            for hotspot
            in nearby_hotspots
        )

        # ----------------------------------------------------
        # MOST RECENT YEAR
        # ----------------------------------------------------

        years = [

            hotspot["year"]

            for hotspot
            in nearby_hotspots

            if hotspot.get(
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
                nearby_hotspots
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
        "HISTORICAL HOTSPOT ENGINE V1"
    )

    print(
        "=============================================="
    )

    try:

        # ----------------------------------------------------
        # CREATE TABLE
        # ----------------------------------------------------

        engine.create_table()

        # ----------------------------------------------------
        # TEST LOCATION
        # ----------------------------------------------------

        result = engine.analyze(

            latitude=22.8046,

            longitude=86.2029
        )

        print(
            "\nSTATUS:",
            result["status"]
        )

        print(
            "Search radius:",
            result[
                "search_radius_m"
            ],
            "m"
        )

        print(
            "Hotspots within 500m:",
            result[
                "hotspots_within_500m"
            ]
        )

        print(
            "Nearest hotspot:",
            result[
                "nearest_hotspot_distance_m"
            ],
            "m"
        )

        print(
            "Historical cases:",
            result[
                "historical_cases_within_500m"
            ]
        )

        print(
            "Most recent year:",
            result[
                "most_recent_hotspot_year"
            ]
        )

    except Exception as error:

        print(
            "\nHotspot Engine test could not run:"
        )

        print(error)

    print(
        "\n=============================================="
    )