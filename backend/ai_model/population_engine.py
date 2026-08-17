import math
import time
import requests


class PopulationEngine:
    """
    LarvaeLens Population Exposure Engine V1.

    Uses the WorldPop API to estimate population inside
    a circular area around the observation location.

    Primary analysis radius:
        500 meters

    Output:
        - estimated population
        - population density
        - area
        - data year
        - source

    IMPORTANT:
        This engine does NOT calculate risk.
    """

    WORLDPOP_API = (
        "https://api.worldpop.org/v2"
    )

    DEFAULT_RADIUS_M = 500

    DEFAULT_YEAR = 2025

    RESOLUTION = "100m"

    MAX_WAIT_SECONDS = 120

    POLL_INTERVAL_SECONDS = 3

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        radius_m=DEFAULT_RADIUS_M,
        year=DEFAULT_YEAR
    ):

        self.radius_m = radius_m
        self.year = year

        print(
            "Population Engine V1 initialized."
        )

        print(
            f"WorldPop year: {self.year}"
        )

        print(
            f"Population radius: "
            f"{self.radius_m} m"
        )

        print(
            f"Resolution: {self.RESOLUTION}"
        )

    # ========================================================
    # HAVERSINE / EARTH GEOMETRY
    # ========================================================

    @staticmethod
    def create_circle_geojson(
        latitude,
        longitude,
        radius_m,
        points=72
    ):
        """
        Create an approximate circular polygon around
        a GPS coordinate.

        GeoJSON uses:
            [longitude, latitude]

        not:
            [latitude, longitude]
        """

        earth_radius_m = 6371000.0

        lat_rad = math.radians(
            latitude
        )

        lon_rad = math.radians(
            longitude
        )

        angular_distance = (
            radius_m
            / earth_radius_m
        )

        coordinates = []

        for i in range(points + 1):

            bearing = (
                2
                * math.pi
                * i
                / points
            )

            point_lat = math.asin(

                math.sin(lat_rad)
                * math.cos(
                    angular_distance
                )

                +

                math.cos(lat_rad)
                * math.sin(
                    angular_distance
                )
                * math.cos(
                    bearing
                )
            )

            point_lon = (

                lon_rad

                +

                math.atan2(

                    math.sin(
                        bearing
                    )
                    * math.sin(
                        angular_distance
                    )
                    * math.cos(
                        lat_rad
                    ),

                    math.cos(
                        angular_distance
                    )

                    -

                    math.sin(
                        lat_rad
                    )
                    * math.sin(
                        point_lat
                    )
                )
            )

            coordinates.append([

                math.degrees(
                    point_lon
                ),

                math.degrees(
                    point_lat
                )
            ])

        return {

            "type": "Polygon",

            "coordinates": [
                coordinates
            ]
        }

    # ========================================================
    # SUBMIT WORLDPOP REQUEST
    # ========================================================

    def submit_population_request(
        self,
        geojson
    ):
        """
        Submit a population calculation to WorldPop.
        """

        payload = {

            "geojson":
                geojson,

            "year":
                self.year,

            "resolution":
                self.RESOLUTION
        }

        response = requests.post(

            f"{self.WORLDPOP_API}/population",

            json=payload,

            timeout=90
        )

        response.raise_for_status()

        data = response.json()

        task_id = data.get(
            "task_id"
        )

        if not task_id:

            raise RuntimeError(
                "WorldPop did not return a task ID."
            )

        return task_id

    # ========================================================
    # WAIT FOR RESULT
    # ========================================================

    def wait_for_result(
        self,
        task_id
    ):
        """
        Poll WorldPop until the population calculation
        finishes.
        """

        start_time = time.time()

        while True:

            elapsed = (
                time.time()
                - start_time
            )

            if (
                elapsed
                > self.MAX_WAIT_SECONDS
            ):

                raise TimeoutError(
                    "WorldPop population "
                    "calculation timed out."
                )

            response = requests.get(

                f"{self.WORLDPOP_API}/tasks/"
                f"{task_id}",

                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            status = data.get(
                "status"
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if status == "success":

                return data

            # ------------------------------------------------
            # FAILURE
            # ------------------------------------------------

            if status == "failure":

                raise RuntimeError(
                    data.get(
                        "error",
                        "WorldPop calculation failed."
                    )
                )

            # ------------------------------------------------
            # STILL PROCESSING
            # ------------------------------------------------

            time.sleep(
                self.POLL_INTERVAL_SECONDS
            )

    # ========================================================
    # POPULATION COLLECTION
    # ========================================================

    def collect(
        self,
        latitude,
        longitude
    ):
        """
        Calculate population within the configured radius.
        """

        # ----------------------------------------------------
        # VALIDATE GPS
        # ----------------------------------------------------

        if (
            latitude is None
            or longitude is None
        ):

            return {

                "population_engine":
                    "population-engine-v1",

                "status":
                    "unavailable",

                "reason":
                    "GPS coordinates unavailable",

                "radius_m":
                    self.radius_m,

                "estimated_population":
                    None,

                "population_density_per_km2":
                    None,

                "area_km2":
                    None,

                "data_year":
                    self.year,

                "resolution":
                    self.RESOLUTION,

                "source":
                    "WorldPop"
            }

        try:

            # ------------------------------------------------
            # CREATE 500m CIRCLE
            # ------------------------------------------------

            geojson = (
                self.create_circle_geojson(

                    latitude,

                    longitude,

                    self.radius_m
                )
            )

            # ------------------------------------------------
            # SUBMIT
            # ------------------------------------------------

            task_id = (
                self.submit_population_request(
                    geojson
                )
            )

            # ------------------------------------------------
            # WAIT
            # ------------------------------------------------

            response = (
                self.wait_for_result(
                    task_id
                )
            )

            result = response.get(
                "result",
                {}
            )

            population = result.get(
                "total_population"
            )

            area_km2 = result.get(
                "area_km2"
            )

            density = result.get(
                "population_density"
            )

            # ------------------------------------------------
            # FINAL RESULT
            # ------------------------------------------------

            return {

                "population_engine":
                    "population-engine-v1",

                "status":
                    "success",

                "location": {

                    "latitude":
                        latitude,

                    "longitude":
                        longitude
                },

                "radius_m":
                    self.radius_m,

                "estimated_population":
                    (
                        round(
                            float(
                                population
                            ),
                            2
                        )

                        if population is not None

                        else None
                    ),

                "population_density_per_km2":
                    (
                        round(
                            float(
                                density
                            ),
                            2
                        )

                        if density is not None

                        else None
                    ),

                "area_km2":
                    (
                        round(
                            float(
                                area_km2
                            ),
                            6
                        )

                        if area_km2 is not None

                        else None
                    ),

                "data_year":
                    result.get(
                        "data_year",
                        self.year
                    ),

                "resolution":
                    self.RESOLUTION,

                "source":
                    result.get(
                        "data_source",
                        "WorldPop"
                    ),

                "task_id":
                    task_id
            }

        except Exception as error:

            print(
                "Population API error:",
                error
            )

            return {

                "population_engine":
                    "population-engine-v1",

                "status":
                    "error",

                "reason":
                    str(error),

                "location": {

                    "latitude":
                        latitude,

                    "longitude":
                        longitude
                },

                "radius_m":
                    self.radius_m,

                "estimated_population":
                    None,

                "population_density_per_km2":
                    None,

                "area_km2":
                    None,

                "data_year":
                    self.year,

                "resolution":
                    self.RESOLUTION,

                "source":
                    "WorldPop"
            }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    engine = PopulationEngine()

    result = engine.collect(

        latitude=22.8046,

        longitude=86.2029
    )

    print(
        "\n=============================================="
    )

    print(
        "POPULATION ENGINE V1"
    )

    print(
        "=============================================="
    )

    print(
        "Status:",
        result["status"]
    )

    print(
        "Location:",
        result.get(
            "location"
        )
    )

    print(
        "Radius:",
        result["radius_m"],
        "m"
    )

    print(
        "Estimated population:",
        result[
            "estimated_population"
        ]
    )

    print(
        "Population density:",
        result[
            "population_density_per_km2"
        ],
        "people/km²"
    )

    print(
        "Area:",
        result["area_km2"],
        "km²"
    )

    print(
        "Data year:",
        result["data_year"]
    )

    print(
        "Resolution:",
        result["resolution"]
    )

    print(
        "Source:",
        result["source"]
    )

    print(
        "=============================================="
    )