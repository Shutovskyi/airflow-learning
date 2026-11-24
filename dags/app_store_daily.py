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
) as dag:
    load_app_store = BashOperator(
        task_id="load_app_store",
        bash_command='python -u "$APP_PROJECT_DIR/scripts/load_app_store.py"',
        retries=2,
        retry_delay=timedelta(minutes=5),
        do_xcom_push=False,
    )