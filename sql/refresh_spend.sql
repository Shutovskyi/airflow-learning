CREATE OR REPLACE TABLE `psychic-diorama-450806-f7.airflow_demo.airflow_spend_demo` AS
SELECT
    CURRENT_DATE('America/Los_Angeles') AS spend_date,
    'demo_app' AS app_id,
    NUMERIC '125.50' AS spend_usd;
