import os
import math
import requests

from datetime import datetime, timezone

from backend.ai_model.population_engine import PopulationEngine
from backend.ai_model.hotspot_engine import HotspotEngine


class EnvironmentalEngine:
    """
    LarvaeLens Environmental Evidence Engine V1.3.4

    Collects:

        1. GPS location
        2. GPS accuracy
        3. Timestamp
        4. Temperature
        5. Humidity
        6. Rainfall - 24 hours
        7. Rainfall - 3 days
        8. Rainfall - 7 days
        9. Nearby schools
        10. Nearby hospitals
        11. Nearby universities
        12. Estimated population within 500 m
        13. Population density within 500 m

    External data sources:

        Weather:
            Open-Meteo

        Nearby facilities:
            Google Places API (New)

        Population:
            WorldPop

    IMPORTANT:

        This engine does NOT calculate risk.

        It only collects environmental and population
        evidence for the Risk Engine.
    """

    # ========================================================
    # API CONFIGURATION
    # ========================================================

    WEATHER_API = (
        "https://api.open-meteo.com/v1/forecast"
    )

    GOOGLE_PLACES_API = (
        "https://places.googleapis.com/v1/places:searchNearby"
    )

    # ========================================================
    # GOOGLE PLACES CONFIGURATION
    # ========================================================

    # Hard geographic search radius
    GOOGLE_RADIUS_M = 1000

    # Google Nearby Search maximum
    GOOGLE_MAX_RESULTS = 20

    # Spatial zones used by LarvaeLens
    SPATIAL_ZONES_M = (
        250,
        500,
        1000
    )

    # ========================================================
    # POPULATION CONFIGURATION
    # ========================================================

    POPULATION_RADIUS_M = 500

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.google_places_api_key = os.getenv(
            "GOOGLE_PLACES_API_KEY"
        )

        # ----------------------------------------------------
        # POPULATION ENGINE
        # ----------------------------------------------------

        self.population_engine = PopulationEngine(
            radius_m=self.POPULATION_RADIUS_M,
            year=2025
        )
        self.hotspot_engine = HotspotEngine(
        radius_m=500
        )

        print(
            "Environmental Engine V1.3.4 initialized."
        )

        if self.google_places_api_key:

            print(
                "Google Places API: configured."
            )

        else:

            print(
                "Google Places API: NOT configured."
            )

    # ========================================================
    # WEATHER
    # ========================================================

    def fetch_weather(
        self,
        latitude,
        longitude
    ):
        """
        Retrieve current weather and historical rainfall
        from Open-Meteo.

        Rainfall windows are calculated using timestamps.
        """

        if (
            latitude is None
            or longitude is None
        ):

            return None

        try:

            params = {

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "rain"
                ),

                "hourly": (
                    "precipitation,"
                    "rain"
                ),

                # Historical period
                "past_days":
                    7,

                # No future forecast required
                "forecast_days":
                    0,

                "timezone":
                    "auto",

                "temperature_unit":
                    "celsius",

                "precipitation_unit":
                    "mm"
            }

            response = requests.get(

                self.WEATHER_API,

                params=params,

                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            current = data.get(
                "current",
                {}
            )

            hourly = data.get(
                "hourly",
                {}
            )

            hourly_times = hourly.get(
                "time",
                []
            )

            precipitation = hourly.get(
                "precipitation",
                []
            )

            current_time_string = current.get(
                "time"
            )

            # ------------------------------------------------
            # RAINFALL WINDOWS
            # ------------------------------------------------

            rainfall_24h = (
                self._rainfall_window(
                    hourly_times,
                    precipitation,
                    current_time_string,
                    24
                )
            )

            rainfall_3d = (
                self._rainfall_window(
                    hourly_times,
                    precipitation,
                    current_time_string,
                    72
                )
            )

            rainfall_7d = (
                self._rainfall_window(
                    hourly_times,
                    precipitation,
                    current_time_string,
                    168
                )
            )

            return {

                "temperature_c":
                    current.get(
                        "temperature_2m"
                    ),

                "humidity_percent":
                    current.get(
                        "relative_humidity_2m"
                    ),

                "rainfall_24h_mm":
                    rainfall_24h,

                "rainfall_3d_mm":
                    rainfall_3d,

                "rainfall_7d_mm":
                    rainfall_7d,

                "current_precipitation_mm":
                    current.get(
                        "precipitation"
                    ),

                "current_rain_mm":
                    current.get(
                        "rain"
                    ),

                "source":
                    "Open-Meteo",

                "weather_timezone":
                    data.get(
                        "timezone"
                    ),

                "weather_coordinates": {

                    "latitude":
                        data.get(
                            "latitude"
                        ),

                    "longitude":
                        data.get(
                            "longitude"
                        )
                }
            }

        except Exception as error:

            print(
                "Weather API error:",
                error
            )

            return None

    # ========================================================
    # RAINFALL WINDOW
    # ========================================================

    @staticmethod
    def _rainfall_window(
        times,
        values,
        current_time_string,
        hours
    ):
        """
        Calculate rainfall during the previous N hours.

        Uses actual timestamps instead of simply selecting
        the last N array values.
        """

        if (
            not times
            or not values
            or not current_time_string
        ):

            return None

        try:

            current_dt = (
                datetime.fromisoformat(
                    current_time_string
                )
            )

            current_timestamp = (
                current_dt.timestamp()
            )

            start_timestamp = (
                current_timestamp
                -
                (
                    hours
                    * 3600
                )
            )

            total = 0.0

            for (
                time_string,
                value
            ) in zip(
                times,
                values
            ):

                observation_dt = (
                    datetime.fromisoformat(
                        time_string
                    )
                )

                observation_timestamp = (
                    observation_dt.timestamp()
                )

                if (

                    start_timestamp
                    <
                    observation_timestamp
                    <=
                    current_timestamp

                ):

                    if value is not None:

                        total += float(
                            value
                        )

            return round(
                total,
                3
            )

        except Exception:

            return None

    # ========================================================
    # HAVERSINE DISTANCE
    # ========================================================

    @staticmethod
    def calculate_distance_m(
        lat1,
        lon1,
        lat2,
        lon2
    ):
        """
        Haversine formula.

        Calculates great-circle distance between two
        geographic coordinates.

        Returns:
            distance in meters.
        """

        earth_radius_m = 6371000.0

        lat1_rad = math.radians(
            lat1
        )

        lat2_rad = math.radians(
            lat2
        )

        delta_lat = math.radians(
            lat2 - lat1
        )

        delta_lon = math.radians(
            lon2 - lon1
        )

        a = (

            math.sin(
                delta_lat / 2
            ) ** 2

            +

            math.cos(
                lat1_rad
            )

            *

            math.cos(
                lat2_rad
            )

            *

            math.sin(
                delta_lon / 2
            ) ** 2
        )

        c = (

            2
            *

            math.atan2(

                math.sqrt(
                    a
                ),

                math.sqrt(
                    1 - a
                )
            )
        )

        return (
            earth_radius_m
            * c
        )

    # ========================================================
    # EMPTY FACILITY RESULT
    # ========================================================

    @staticmethod
    def empty_facility_result(
        category,
        reason=None
    ):
        """
        Standard facility result structure.
        """

        return {

            "status":
                "unavailable"
                if reason
                else "success",

            "category":
                category,

            "reason":
                reason,

            "search_radius_m":
                1000,

            "requested_primary_types":
                [],

            "returned_count":
                0,

            "unique_count":
                0,

            "result_limit_reached":
                False,

            "nearest_distance_m":
                None,

            "spatial_summary": {

                "within_250m":
                    0,

                "within_500m":
                    0,

                "within_1km":
                    0
            },

            "places":
                []
        }

    # ========================================================
    # SPATIAL SUMMARY
    # ========================================================

    @staticmethod
    def build_spatial_summary(
        places
    ):
        """
        Build cumulative spatial counts.

        <= 250 m
        <= 500 m
        <= 1 km
        """

        distances = [

            place["distance_m"]

            for place in places

            if place.get(
                "distance_m"
            ) is not None
        ]

        return {

            "within_250m":
                sum(

                    distance <= 250

                    for distance
                    in distances
                ),

            "within_500m":
                sum(

                    distance <= 500

                    for distance
                    in distances
                ),

            "within_1km":
                sum(

                    distance <= 1000

                    for distance
                    in distances
                )
        }

    # ========================================================
    # GOOGLE PLACES SEARCH
    # ========================================================

    def search_nearby_places(
        self,
        latitude,
        longitude,
        primary_types,
        category_name
    ):
        """
        Search Google Places using primary types.

        Google Nearby Search returns a maximum of 20
        results for a request.

        Therefore:

            returned_count = 20

        does NOT necessarily mean there are exactly
        20 facilities.
        """

        # ----------------------------------------------------
        # GPS VALIDATION
        # ----------------------------------------------------

        if (
            latitude is None
            or longitude is None
        ):

            return self.empty_facility_result(

                category_name,

                "GPS coordinates unavailable"
            )

        # ----------------------------------------------------
        # API KEY VALIDATION
        # ----------------------------------------------------

        if not self.google_places_api_key:

            return self.empty_facility_result(

                category_name,

                "Google Places API key not configured"
            )

        # ----------------------------------------------------
        # HEADERS
        # ----------------------------------------------------

        headers = {

            "Content-Type":
                "application/json",

            "X-Goog-Api-Key":
                self.google_places_api_key,

            "X-Goog-FieldMask":

                "places.id,"
                "places.displayName,"
                "places.location,"
                "places.types,"
                "places.primaryType"
        }

        # ----------------------------------------------------
        # REQUEST BODY
        # ----------------------------------------------------

        body = {

            "includedPrimaryTypes":
                primary_types,

            "maxResultCount":
                self.GOOGLE_MAX_RESULTS,

            "rankPreference":
                "DISTANCE",

            "locationRestriction": {

                "circle": {

                    "center": {

                        "latitude":
                            latitude,

                        "longitude":
                            longitude
                    },

                    "radius":
                        float(
                            self.GOOGLE_RADIUS_M
                        )
                }
            }
        }

        try:

            response = requests.post(

                self.GOOGLE_PLACES_API,

                headers=headers,

                json=body,

                timeout=20
            )

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            if response.status_code != 200:

                try:

                    error_data = (
                        response.json()
                    )

                except Exception:

                    error_data = (
                        response.text
                    )

                print(

                    f"Google Places "
                    f"{category_name} error: "
                    f"{response.status_code}"
                )

                print(
                    "Google response:",
                    error_data
                )

                return self.empty_facility_result(

                    category_name,

                    f"HTTP {response.status_code}"
                )

            data = response.json()

            raw_places = data.get(
                "places",
                []
            )

            returned_count = len(
                raw_places
            )

            # ------------------------------------------------
            # RESULT LIMIT
            # ------------------------------------------------

            result_limit_reached = (

                returned_count
                >=
                self.GOOGLE_MAX_RESULTS
            )

            places = []

            # =================================================
            # PROCESS PLACES
            # =================================================

            for place in raw_places:

                # ------------------------------------------------
                # PLACE ID
                # ------------------------------------------------

                place_id = place.get(
                    "id"
                )

                if not place_id:

                    continue

                # ------------------------------------------------
                # PRIMARY TYPE
                # ------------------------------------------------

                returned_primary_type = (
                    place.get(
                        "primaryType"
                    )
                )

                # Strict category validation
                if (

                    returned_primary_type
                    not in
                    primary_types

                ):

                    continue

                # ------------------------------------------------
                # LOCATION
                # ------------------------------------------------

                location = place.get(
                    "location",
                    {}
                )

                place_lat = location.get(
                    "latitude"
                )

                place_lon = location.get(
                    "longitude"
                )

                if (

                    place_lat is None
                    or
                    place_lon is None

                ):

                    continue

                # ------------------------------------------------
                # DISTANCE
                # ------------------------------------------------

                distance = (
                    self.calculate_distance_m(

                        latitude,

                        longitude,

                        place_lat,

                        place_lon
                    )
                )

                # ------------------------------------------------
                # HARD 1 KM FILTER
                # ------------------------------------------------

                if (

                    distance
                    >
                    self.GOOGLE_RADIUS_M

                ):

                    continue

                # ------------------------------------------------
                # NAME
                # ------------------------------------------------

                display_name = place.get(
                    "displayName",
                    {}
                )

                place_name = (
                    display_name.get(
                        "text"
                    )
                )

                # ------------------------------------------------
                # STORE
                # ------------------------------------------------

                places.append({

                    "place_id":
                        place_id,

                    "name":
                        place_name,

                    "latitude":
                        place_lat,

                    "longitude":
                        place_lon,

                    "distance_m":
                        round(
                            distance,
                            2
                        ),

                    "primary_type":
                        returned_primary_type,

                    "types":
                        place.get(
                            "types",
                            []
                        )
                })

            # =================================================
            # DEDUPLICATION
            # =================================================

            unique_places = {}

            for place in places:

                place_id = place.get(
                    "place_id"
                )

                if place_id:

                    unique_places[
                        place_id
                    ] = place

            places = list(
                unique_places.values()
            )

            # =================================================
            # SORT
            # =================================================

            places.sort(

                key=lambda place:
                    place["distance_m"]
            )

            # =================================================
            # NEAREST
            # =================================================

            nearest_distance = (

                places[0][
                    "distance_m"
                ]

                if places

                else None
            )

            # =================================================
            # SPATIAL SUMMARY
            # =================================================

            spatial_summary = (
                self.build_spatial_summary(
                    places
                )
            )

            # =================================================
            # FINAL RESULT
            # =================================================

            return {

                "status":
                    "success",

                "category":
                    category_name,

                "requested_primary_types":
                    primary_types,

                "search_radius_m":
                    self.GOOGLE_RADIUS_M,

                "returned_count":
                    returned_count,

                "unique_count":
                    len(
                        places
                    ),

                "result_limit_reached":
                    result_limit_reached,

                "nearest_distance_m":
                    nearest_distance,

                "spatial_summary":
                    spatial_summary,

                "places":
                    places
            }

        except requests.RequestException as error:

            print(

                f"Google Places "
                f"{category_name} network error:",
                error
            )

            return self.empty_facility_result(

                category_name,

                str(error)
            )

        except Exception as error:

            print(

                f"Google Places "
                f"{category_name} exception:",
                error
            )

            return self.empty_facility_result(

                category_name,

                str(error)
            )

    # ========================================================
    # ALL NEARBY FACILITIES
    # ========================================================

    def fetch_nearby_facilities(
        self,
        latitude,
        longitude
    ):
        """
        Collect:

            schools
            hospitals
            universities

        Higher education currently uses Google's
        supported 'university' primary type.

        We do NOT use 'college' because Google Places
        rejects 'college' as an unsupported primary type.
        """

        # ----------------------------------------------------
        # SCHOOLS
        # ----------------------------------------------------

        schools = (
            self.search_nearby_places(

                latitude,

                longitude,

                ["school"],

                "schools"
            )
        )

        # ----------------------------------------------------
        # HOSPITALS
        # ----------------------------------------------------

        hospitals = (
            self.search_nearby_places(

                latitude,

                longitude,

                ["hospital"],

                "hospitals"
            )
        )

        # ----------------------------------------------------
        # UNIVERSITIES
        # ----------------------------------------------------

        universities = (
            self.search_nearby_places(

                latitude,

                longitude,

                ["university"],

                "universities"
            )
        )

        # ----------------------------------------------------
        # HIGHER EDUCATION
        # ----------------------------------------------------

        higher_education = {

            "status":
                universities.get(
                    "status",
                    "unavailable"
                ),

            "category":
                "higher_education",

            "search_radius_m":
                self.GOOGLE_RADIUS_M,

            "returned_count":
                universities.get(
                    "returned_count",
                    0
                ),

            "unique_count":
                universities.get(
                    "unique_count",
                    0
                ),

            "result_limit_reached":
                universities.get(
                    "result_limit_reached",
                    False
                ),

            "nearest_distance_m":
                universities.get(
                    "nearest_distance_m"
                ),

            "spatial_summary":
                universities.get(

                    "spatial_summary",

                    {

                        "within_250m":
                            0,

                        "within_500m":
                            0,

                        "within_1km":
                            0
                    }
                ),

            "places":
                universities.get(
                    "places",
                    []
                )
        }

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        return {

            "provider":
                "Google Places API (New)",

            "search_radius_m":
                self.GOOGLE_RADIUS_M,

            "zones_m":
                self.SPATIAL_ZONES_M,

            "schools":
                schools,

            "hospitals":
                hospitals,

            "higher_education":
                higher_education
        }

    # ========================================================
    # POPULATION
    # ========================================================

    def fetch_population(
        self,
        latitude,
        longitude
    ):
        """
        Run Population Engine V1.

        Primary radius:
            500 m
        """

        try:

            return (
                self.population_engine.collect(

                    latitude=latitude,

                    longitude=longitude
                )
            )

        except Exception as error:

            print(
                "Population Engine error:",
                error
            )

            return {

                "population_engine":
                    "population-engine-v1",

                "status":
                    "error",

                "reason":
                    str(error),

                "radius_m":
                    self.POPULATION_RADIUS_M,

                "estimated_population":
                    None,

                "population_density_per_km2":
                    None,

                "area_km2":
                    None,

                "data_year":
                    2025,

                "resolution":
                    "100m",

                "source":
                    "WorldPop"
            }
    # ========================================================
    # HISTORICAL HOTSPOTS
    # ========================================================

    def fetch_historical_hotspots(
        self,
        latitude,
        longitude
    ):
        """
        Run Historical Hotspot Engine.

        Primary analysis radius:
        500 m

    This method only retrieves historical evidence.
    It does NOT calculate risk.
        """

        try:

            return self.hotspot_engine.analyze(
            latitude=latitude,
            longitude=longitude
        )

        except Exception as error:

            print(
            "Historical Hotspot Engine error:",
            error
        )

        return {
            "hotspot_engine":
                "historical-hotspot-engine-v1",

            "status":
                "error",

            "search_radius_m":
                500,

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

    # ========================================================
    # MAIN COLLECTION
    # ========================================================

    def collect(

        self,

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

        timestamp=None
    ):
        """
        Collect all environmental evidence.

        Explicit weather values supplied by the caller
        take priority.

        Missing weather values are obtained from Open-Meteo.

        Population is obtained from WorldPop.

        Historical hotspot values remain available for
        future database integration.
        """

        # ====================================================
        # TIMESTAMP
        # ====================================================

        if timestamp is None:

            timestamp = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

        # ====================================================
        # WEATHER
        # ====================================================

        weather = (
            self.fetch_weather(

                latitude,

                longitude
            )
        )

        if weather is not None:

            if temperature_c is None:

                temperature_c = (
                    weather.get(
                        "temperature_c"
                    )
                )

            if humidity_percent is None:

                humidity_percent = (
                    weather.get(
                        "humidity_percent"
                    )
                )

            if rainfall_24h_mm is None:

                rainfall_24h_mm = (
                    weather.get(
                        "rainfall_24h_mm"
                    )
                )

            if rainfall_3d_mm is None:

                rainfall_3d_mm = (
                    weather.get(
                        "rainfall_3d_mm"
                    )
                )

            if rainfall_7d_mm is None:

                rainfall_7d_mm = (
                    weather.get(
                        "rainfall_7d_mm"
                    )
                )

        # ====================================================
        # POPULATION
        # ====================================================

        population = (
            self.fetch_population(

                latitude,

                longitude
            )
        )

        # ====================================================
        # FACILITIES
        # ====================================================

        facilities = (
            self.fetch_nearby_facilities(

                latitude,

                longitude
            )
        )

        # ====================================================
        # HISTORICAL HOTSPOTS
        # ====================================================

        historical_risk = (
            self.fetch_historical_hotspots(
                latitude,
                longitude
            )
        )

        # ====================================================
        # FINAL RESULT
        # ====================================================

        return {

            "environment_engine":
                "environmental-engine-v1.3.4",

            # ------------------------------------------------
            # LOCATION
            # ------------------------------------------------

            "location": {

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "accuracy_m":
                    accuracy_m
            },

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            "time": {

                "timestamp":
                    timestamp
            },

            # ------------------------------------------------
            # WEATHER
            # ------------------------------------------------

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

                "current_precipitation_mm":
                    (
                        weather.get(
                            "current_precipitation_mm"
                        )

                        if weather

                        else None
                    ),

                "current_rain_mm":
                    (
                        weather.get(
                            "current_rain_mm"
                        )

                        if weather

                        else None
                    ),

                "source":
                    (
                        weather.get(
                            "source"
                        )

                        if weather

                        else None
                    ),

                "weather_timezone":
                    (
                        weather.get(
                            "weather_timezone"
                        )

                        if weather

                        else None
                    ),

                "weather_coordinates":
                    (
                        weather.get(
                            "weather_coordinates"
                        )

                        if weather

                        else None
                    )
            },

            # ------------------------------------------------
            # POPULATION
            # ------------------------------------------------

            "population": {

                "status":
                    population.get(
                        "status"
                    ),

                "search_radius_m":
                    population.get(
                        "radius_m",
                        self.POPULATION_RADIUS_M
                    ),

                "estimated_population_500m":
                    (
                        population.get(
                            "estimated_population"
                        )

                        if population.get(
                            "status"
                        ) == "success"

                        else estimated_population
                    ),

                "population_density_500m":
                    (
                        population.get(
                            "population_density_per_km2"
                        )

                        if population.get(
                            "status"
                        ) == "success"

                        else population_density
                    ),

                "area_km2":
                    population.get(
                        "area_km2"
                    ),

                "data_year":
                    population.get(
                        "data_year"
                    ),

                "resolution":
                    population.get(
                        "resolution"
                    ),

                "source":
                    population.get(
                        "source"
                    )
            },

            # ------------------------------------------------
            # NEARBY FACILITIES
            # ------------------------------------------------

            "nearby_facilities":
                facilities,

            # ------------------------------------------------
            # HISTORICAL RISK
            # ------------------------------------------------

            "historical_risk": {

                "status": historical_risk.get("status"),
                    

                "search_radius_m":historical_risk.get(
                                  "search_radius_m",
                                    500
                                       ),


                "hotspots_within_500m": historical_risk.get(
                                        "hotspots_within_500m"
                                          ),

                "nearest_hotspot_distance_m": historical_risk.get(
                                              "nearest_hotspot_distance_m"
                                             ),

                "historical_cases_within_500m": historical_risk.get(
                                                "historical_cases_within_500m"
                                                  ),

                "most_recent_hotspot_year": historical_risk.get("most_recent_hotspot_year"
                                             ),

                "source":
                    "LarvaeLens historical database"
            }
        }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    engine = EnvironmentalEngine()

    result = engine.collect(

        latitude=22.8046,

        longitude=86.2029,

        accuracy_m=8.5
    )

    print(
        "\n=============================================="
    )

    print(
        "ENVIRONMENTAL ENGINE V1.3.4"
    )

    print(
        "=============================================="
    )

    # ========================================================
    # LOCATION
    # ========================================================

    location = result[
        "location"
    ]

    print(
        "\nLOCATION"
    )

    print(
        "Latitude :",
        location["latitude"]
    )

    print(
        "Longitude:",
        location["longitude"]
    )

    print(
        "Accuracy :",
        location["accuracy_m"],
        "m"
    )

    # ========================================================
    # WEATHER
    # ========================================================

    weather = result[
        "weather"
    ]

    print(
        "\nWEATHER"
    )

    print(
        "Temperature:",
        weather["temperature_c"],
        "°C"
    )

    print(
        "Humidity:",
        weather["humidity_percent"],
        "%"
    )

    print(
        "Rainfall 24h:",
        weather["rainfall_24h_mm"],
        "mm"
    )

    print(
        "Rainfall 3d:",
        weather["rainfall_3d_mm"],
        "mm"
    )

    print(
        "Rainfall 7d:",
        weather["rainfall_7d_mm"],
        "mm"
    )

    print(
        "Weather source:",
        weather["source"]
    )

    # ========================================================
    # POPULATION
    # ========================================================

    population = result[
        "population"
    ]

    print(
        "\nPOPULATION"
    )

    print(
        "Status:",
        population["status"]
    )

    print(
        "Search radius:",
        population[
            "search_radius_m"
        ],
        "m"
    )

    print(
        "Estimated population 500m:",
        population[
            "estimated_population_500m"
        ]
    )

    print(
        "Population density 500m:",
        population[
            "population_density_500m"
        ],
        "people/km²"
    )

    print(
        "Area:",
        population[
            "area_km2"
        ],
        "km²"
    )

    print(
        "Data year:",
        population[
            "data_year"
        ]
    )

    print(
        "Resolution:",
        population[
            "resolution"
        ]
    )

    print(
        "Population source:",
        population[
            "source"
        ]
    )

    # ========================================================
    # FACILITIES
    # ========================================================

    facilities = result[
        "nearby_facilities"
    ]

    print(
        "\nNEARBY FACILITIES"
    )

    print(
        "Provider:",
        facilities[
            "provider"
        ]
    )

    print(
        "Search radius:",
        facilities[
            "search_radius_m"
        ],
        "m"
    )

    # --------------------------------------------------------
    # SCHOOLS / HOSPITALS
    # --------------------------------------------------------

    for category in (
        "schools",
        "hospitals"
    ):

        data = facilities[
            category
        ]

        print(
            f"\n{category.upper()}"
        )

        print(
            "Google returned:",
            data[
                "returned_count"
            ]
        )

        print(
            "Unique validated:",
            data[
                "unique_count"
            ]
        )

        print(
            "Result limit reached:",
            data[
                "result_limit_reached"
            ]
        )

        print(
            "Nearest:",
            data[
                "nearest_distance_m"
            ],
            "m"
        )

        summary = data[
            "spatial_summary"
        ]

        print(
            "Within 250 m:",
            summary[
                "within_250m"
            ]
        )

        print(
            "Within 500 m:",
            summary[
                "within_500m"
            ]
        )

        print(
            "Within 1 km:",
            summary[
                "within_1km"
            ]
        )

    # --------------------------------------------------------
    # HIGHER EDUCATION
    # --------------------------------------------------------

    higher = facilities[
        "higher_education"
    ]

    print(
        "\nHIGHER EDUCATION"
    )

    print(
        "Google returned:",
        higher[
            "returned_count"
        ]
    )

    print(
        "Unique validated:",
        higher[
            "unique_count"
        ]
    )

    print(
        "Result limit reached:",
        higher[
            "result_limit_reached"
        ]
    )

    print(
        "Nearest:",
        higher[
            "nearest_distance_m"
        ],
        "m"
    )

    summary = higher[
        "spatial_summary"
    ]

    print(
        "Within 250 m:",
        summary[
            "within_250m"
        ]
    )

    print(
        "Within 500 m:",
        summary[
            "within_500m"
        ]
    )

    print(
        "Within 1 km:",
        summary[
            "within_1km"
        ]
    )

    # ========================================================
    # HISTORICAL HOTSPOT STATUS
    # ========================================================

    historical = result[
        "historical_risk"
    ]

    print(
        "\nHISTORICAL HOTSPOT"
    )

    print(
        "Status:",
        historical[
            "status"
        ]
    )

    print(
        "Search radius:",
        historical[
            "search_radius_m"
        ],
        "m"
    )

    print(
        "Hotspots within 500m:",
        historical[
            "hotspots_within_500m"
        ]
    )

    print(
        "Historical cases within 500m:",
        historical[
            "historical_cases_within_500m"
        ]
    )

    print(
        "\n=============================================="
    )