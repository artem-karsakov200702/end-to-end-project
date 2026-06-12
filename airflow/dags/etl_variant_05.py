import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

CONFIG_PATH = "/opt/airflow/project/configs/variant_05.yml"
PROJECT_DIR = "/opt/airflow/project"

with DAG(
    dag_id="etl_variant_05",
    description="Weather ETL: extract -> transform -> dq -> load (variant 05, week12)",
    start_date=pendulum.datetime(2026, 3, 1, tz="UTC"),
    schedule="@daily",
    catchup=True,
    tags=["week12", "weather", "variant_05"],
) as dag:

    extract = BashOperator(
        task_id="extract",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python -m src.pipeline "
            f"--config {CONFIG_PATH} "
            f"--mode extract "
            f"--start '{{{{ data_interval_start.to_iso8601_string() }}}}' "
            f"--end '{{{{ data_interval_end.to_iso8601_string() }}}}' "
            f"--ds '{{{{ ds }}}}'"
        ),
    )

    transform = BashOperator(
        task_id="transform",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python -m src.pipeline "
            f"--config {CONFIG_PATH} "
            f"--mode transform "
            f"--start '{{{{ data_interval_start.to_iso8601_string() }}}}' "
            f"--end '{{{{ data_interval_end.to_iso8601_string() }}}}' "
            f"--ds '{{{{ ds }}}}'"
        ),
    )

    dq = BashOperator(
        task_id="dq",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python -m src.pipeline "
            f"--config {CONFIG_PATH} "
            f"--mode dq "
            f"--start '{{{{ data_interval_start.to_iso8601_string() }}}}' "
            f"--end '{{{{ data_interval_end.to_iso8601_string() }}}}' "
            f"--ds '{{{{ ds }}}}'"
        ),
    )

    load = BashOperator(
        task_id="load",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python -m src.pipeline "
            f"--config {CONFIG_PATH} "
            f"--mode load "
            f"--start '{{{{ data_interval_start.to_iso8601_string() }}}}' "
            f"--end '{{{{ data_interval_end.to_iso8601_string() }}}}' "
            f"--ds '{{{{ ds }}}}'"
        ),
    )

    extract >> transform >> dq >> load