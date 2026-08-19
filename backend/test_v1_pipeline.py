import json

from ai_model.vision_engine import VisionEngine


IMAGE_PATH = (
    r"C:\Users\siddh\Documents\Codex\2026-08-11"
    r"\inspect-open-stagnant-water-zip-and"
    r"\outputs\model3_balanced\test\images"
    r"\unit_0634__image173.jpeg"
)

LATITUDE = 22.8046
LONGITUDE = 86.2029
ACCURACY_M = 8.5


def main():

    print("==============================================")
    print("LARVAELENS V1 PIPELINE TEST")
    print("==============================================")

    engine = VisionEngine()

    result = engine.analyze(
        IMAGE_PATH,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        accuracy_m=ACCURACY_M,
    )

    print("\n==============================================")
    print("PIPELINE RESULT")
    print("==============================================")

    print(
        json.dumps(
            result,
            indent=2,
            default=str
        )
    )

    print("\n==============================================")
    print("PIPELINE TEST COMPLETE")
    print("==============================================")


if __name__ == "__main__":
    main()