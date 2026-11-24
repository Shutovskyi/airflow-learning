import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from sqlalchemy import create_engine, text


COUNTRY = "US"
BATCH_SIZE = 200
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def load_app_store(engine):
    snapshot_date = datetime.now(timezone.utc).date()

    select_apps = text((SQL_DIR / "select_daily_apps.sql").read_text(encoding="utf-8"))
    upsert_daily = text((SQL_DIR / "upsert_app_daily.sql").read_text(encoding="utf-8"))

    with engine.connect() as connection:
        app_ids = connection.execute(select_apps).scalars().all()

    print(f"Дата: {snapshot_date} | Страна: {COUNTRY} | Выбрано: {len(app_ids)}")

    rows = []

    with requests.Session() as session:
        for start in range(0, len(app_ids), BATCH_SIZE):
            if start > 0:
                time.sleep(3)

            batch = app_ids[start:start + BATCH_SIZE]
            batch_ids = {str(app_id): app_id for app_id in batch}

            response = session.get(
                "https://itunes.apple.com/lookup",
                params={"id": ",".join(batch_ids), "country": COUNTRY.lower()},
                timeout=30,
            )
            response.raise_for_status()

            batch_count = 0

            for app in response.json()["results"]:
                track_id = str(app["trackId"])
                if track_id not in batch_ids:
                    continue

                rows.append({
                    "snapshot_date": snapshot_date,
                    "country": COUNTRY,
                    "app_id": batch_ids[track_id],
                    "app_name": app.get("trackName"),
                    "app_version": app.get("version"),
                    "rating": app.get("averageUserRating"),
                    "ratings_count": app.get("userRatingCount"),
                    "primary_genre": app.get("primaryGenreName"),
                })
                batch_count += 1

            print(
                f"Батч {start // BATCH_SIZE + 1} | "
                f"Запрошено: {len(batch)} | Получено: {batch_count}"
            )

    # Одна транзакция на всю выгрузку
    if rows:
        with engine.begin() as connection:
            connection.execute(upsert_daily, rows)

    print(f"Запись в Neon завершена | public.app_daily | Записано строк: {len(rows)}")


if __name__ == "__main__":
    engine = create_engine(os.environ["DATABASE_URL"])
    load_app_store(engine)