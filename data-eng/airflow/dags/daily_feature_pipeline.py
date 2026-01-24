"""
GraphGuard - Daily Feature Pipeline DAG
=========================================
File: data-eng/airflow/dags/daily_feature_pipeline.py
Reference: Specification.md Lines 1132-1225

Goal: Orchestrate daily feature engineering pipeline.

DAG Steps:
1. validate_transactions - Great Expectations
2. spark_feature_engineering - Compute features
3. run_graph_algorithms - Neo4j PageRank, Louvain
4. export_graph_features - To Parquet
5. materialize_feast - Push to Redis
6. validate_features - Data quality checks
7. trigger_model_retraining - If validation passes

Gotchas (from spec):
- Use catchup=False to avoid backfilling on first deploy
- max_active_runs=1 prevents concurrent DAG runs (data corruption risk)
"""

import os
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.trigger_rule import TriggerRule


# ============================================
# Default Arguments (Spec Lines 1142-1150)
# ============================================

default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email': ['oncall@graphguard.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}


# ============================================
# Task Functions
# ============================================

def run_great_expectations_suite(suite_name: str, **context) -> bool:
    """
    Run Great Expectations validation suite.
    Reference: Specification.md Lines 1227-1280
    """
    import great_expectations as gx
    from great_expectations.checkpoint import SimpleCheckpoint
    
    ge_context = gx.get_context(context_root_dir="/opt/airflow/great_expectations")

    # Ensure expectation suite exists
    suite = None
    suite_module_path = Path(__file__).resolve().parents[2] / "great_expectations" / "checkpoints" / "transaction_quality.py"
    if suite_module_path.exists():
        spec = importlib.util.spec_from_file_location("transaction_quality", suite_module_path)
        module = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(module)
            if suite_name == "transaction_quality":
                suite = module.create_transaction_quality_suite()
            elif suite_name == "feature_quality":
                suite = module.create_feature_quality_suite()
    if suite is not None:
        ge_context.add_or_update_expectation_suite(expectation_suite=suite)
    
    checkpoint = SimpleCheckpoint(
        name=f"{suite_name}_checkpoint",
        data_context=ge_context,
        validations=[{
            "batch_request": {
                "datasource_name": "graphguard_datasource",
                "data_asset_name": suite_name,
                "data_connector_name": "default_runtime_data_connector_name"
            },
            "expectation_suite_name": suite_name
        }]
    )
    checkpoint_result = checkpoint.run()
    
    if not checkpoint_result.success:
        raise ValueError(f"Data quality validation failed: {suite_name}")
    
    return True


def export_graph_features_to_feast(**context) -> None:
    """Export graph features from Neo4j to Feast offline store."""
    module_path = Path(__file__).resolve().parents[2] / "neo4j" / "export_graph_features.py"
    spec = importlib.util.spec_from_file_location("export_graph_features", module_path)
    module = importlib.util.module_from_spec(spec)
    if not spec or not spec.loader:
        raise ImportError("Unable to load export_graph_features module")
    spec.loader.exec_module(module)
    GraphFeaturesExporter = module.GraphFeaturesExporter
    
    exporter = GraphFeaturesExporter()
    try:
        exporter.export_graph_features("s3://graphguard/features/graph_features.parquet")
    finally:
        exporter.close()


def materialize_feast_features(**context) -> None:
    """Materialize features to Feast online store."""
    import subprocess
    from datetime import datetime
    
    end_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    subprocess.run(
        ["feast", "materialize-incremental", end_date],
        cwd="/opt/airflow/feast_repo",
        check=True
    )


# ============================================
# DAG Definition (Spec Lines 1152-1221)
# ============================================

with DAG(
    'daily_feature_pipeline',
    default_args=default_args,
    description='Daily pipeline for feature engineering and materialization',
    schedule_interval='@daily',
    catchup=False,  # Gotcha: avoid backfill on first deploy
    max_active_runs=1,  # Gotcha: prevent concurrent runs
    tags=['data-eng', 'feature-engineering']
) as dag:
    
    # 1. Validate raw transaction data
    validate_transactions = PythonOperator(
        task_id='validate_transactions',
        python_callable=run_great_expectations_suite,
        op_kwargs={'suite_name': 'transaction_quality'}
    )
    
    # 2. Run Spark feature engineering
    spark_features = BashOperator(
        task_id='spark_feature_engineering',
        bash_command="""
        spark-submit \
            --master yarn \
            --deploy-mode cluster \
            --conf spark.executor.instances=10 \
            --conf spark.executor.memory=8g \
            --conf spark.executor.cores=4 \
            s3://graphguard/spark/feature_engineering.py \
            --input s3://graphguard/transactions/ \
            --output s3://graphguard/features/transaction_features/ \
            --date {{ ds }}
        """
    )
    
    # 3. Run Neo4j graph algorithms
    neo4j_algorithms = BashOperator(
        task_id='run_graph_algorithms',
        bash_command="""
        cypher-shell -u neo4j -p ${NEO4J_PASSWORD} << 'EOF'
            CALL gds.graph.project('transaction-graph', 'User', 'TRANSACTED_WITH');
            CALL gds.pageRank.write('transaction-graph', {writeProperty: 'pagerank'});
            CALL gds.louvain.write('transaction-graph', {writeProperty: 'community_id'});
            CALL gds.betweenness.write('transaction-graph', {writeProperty: 'betweenness'});
            CALL gds.graph.drop('transaction-graph');
        EOF
        """
    )
    
    # 4. Export graph features to Parquet
    export_graph = PythonOperator(
        task_id='export_graph_features',
        python_callable=export_graph_features_to_feast
    )
    
    # 5. Materialize to Feast online store (Redis)
    materialize_feast = PythonOperator(
        task_id='materialize_feast',
        python_callable=materialize_feast_features
    )
    
    # 6. Validate computed features
    validate_features = PythonOperator(
        task_id='validate_features',
        python_callable=run_great_expectations_suite,
        op_kwargs={'suite_name': 'feature_quality'}
    )
    
    # 7. Trigger model retraining (if validation passes)
    trigger_retraining = TriggerDagRunOperator(
        task_id='trigger_model_retraining',
        trigger_dag_id='model_retraining_pipeline',
        execution_date='{{ ds }}',
        trigger_rule=TriggerRule.ALL_SUCCESS
    )
    
    # ============================================
    # DAG Dependencies (Spec Lines 1217-1221)
    # ============================================
    
    validate_transactions >> spark_features
    spark_features >> [neo4j_algorithms, export_graph]
    [neo4j_algorithms, export_graph] >> materialize_feast
    materialize_feast >> validate_features
    validate_features >> trigger_retraining
