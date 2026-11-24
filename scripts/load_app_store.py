import argparse
import hashlib
import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import create_engine, text
from urllib3.util.retry import Retry


COUNTRY = "US"
BATCH_SIZE = 200
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
DATA_DIR = Path.home() / "airflow-data" / "app_store_daily"


def download_apps(engine, snapshot_file):
    snapshot_date = datetime.now(timezone.utc).date().isoformat()

    select_apps = text(
        (SQL_DIR / "select_daily_apps.sql").read_text(encoding="utf-8")
    )
    with engine.connect() as connection:
        app_ids = connection.execute(select_apps).scalars().all()

    print(f"Дата: {snapshot_date} | Страна: {COUNTRY} | Выбрано: {len(app_ids)}")

    rows = []
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))

        for start in range(0, len(app_ids), BATCH_SIZE):
            if start > 0:
                time.sleep(3)

            batch = app_ids[start:start + BATCH_SIZE]
            batch_ids = {str(app_id): app_id for app_id in batch}

            response = session.get(
                "https://itunes.apple.com/lookup",
                params={"id": ",".join(batch_ids), "country": COUNTRY.lower()},
                timeout=(10, 60),
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

    # Файл становится доступен второй задаче после записи всех батчей
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = snapshot_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(snapshot_file)

    print(f"Скачано приложений: {len(rows)} | Файл: {snapshot_file}")


def load_dataframe(engine, snapshot_file):
    rows = json.loads(snapshot_file.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows, dtype=object)

    print(f"Создан DataFrame | Строк: {len(df)} | Колонок: {len(df.columns)}")

    if df.empty:
        print("В выгрузке 0 приложений | Записано строк: 0")
        return

    df["snapshot_date"] = df["snapshot_date"].map(date.fromisoformat)

    upsert_daily = text(
        (SQL_DIR / "upsert_app_daily.sql").read_text(encoding="utf-8")
    )

    with engine.begin() as connection:
        connection.execute(upsert_daily, df.to_dict(orient="records"))

    print(f"Запись в Neon завершена | public.app_daily | Записано строк: {len(df)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["download", "load"])
    args = parser.parse_args()

    # У двух задач одного запуска общий файл, у разных запусков — разные файлы
    run_id = os.environ["RUN_ID"]
    filename = hashlib.sha256(run_id.encode()).hexdigest() + ".json"
    snapshot_file = DATA_DIR / filename

    engine = create_engine(os.environ["DATABASE_URL"])

    if args.action == "download":
        download_apps(engine, snapshot_file)
    else:
        load_dataframe(engine, snapshot_file)