from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


with DAG(
    dag_id="app_store_daily",
    start_date=pendulum.datetime(2026, 11, 23, tz="UTC"),
    schedule="0 8 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
) as dag:

    download_apps = BashOperator(
        task_id="download_apps",
        bash_command='python -u "$APP_PROJECT_DIR/scripts/load_app_store.py" download',
        env={"RUN_ID": "{{ run_id }}"},
        append_env=True,
        do_xcom_push=False,
    )

    load_dataframe = BashOperator(
        task_id="load_dataframe",
        bash_command='python -u "$APP_PROJECT_DIR/scripts/load_app_store.py" load',
        env={"RUN_ID": "{{ run_id }}"},
        append_env=True,
        do_xcom_push=False,
    )

    download_apps >> load_dataframe