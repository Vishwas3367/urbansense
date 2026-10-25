from sqlalchemy import text

from .database import Base, engine
from . import models  # noqa: F401


def main() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS manual_trigger BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS temperature_alert BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS impact_detected BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS impact_peak_g FLOAT"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS motion_features JSON"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS event_classification VARCHAR(40)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE sensor_events "
                "ADD COLUMN IF NOT EXISTS pothole_confidence FLOAT"
            )
        )
    print("UrbanSense PostGIS schema is ready.")


if __name__ == "__main__":
    main()
