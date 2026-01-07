"""
Airflow DAG for Automatic Ensemble Model Retraining

Schedule: Weekly (every Monday at 2 AM)

Workflow:
1. Check which models need retraining
2. Fetch latest data from database
3. Retrain models
4. Evaluate new vs old models
5. Deploy if better
6. Send notification
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add project to path
sys.path.insert(0, '/opt/airflow/src')

from prediction.ensemble_stacking import EnsembleStacking
from prediction.utils.feature_engineering import create_features, prepare_training_data


# VN30 stocks to retrain
VN30_STOCKS = [
    'VCB', 'VHM', 'VIC', 'HPG', 'VNM', 'MSN', 'MWG', 'FPT', 'GAS', 'BID',
    'CTG', 'TCB', 'VPB', 'MBB', 'HDB', 'PLX', 'GVR', 'SAB', 'VRE', 'BCM'
]

HORIZONS = ['3day', '48day']


def check_retraining_needed(**context):
    """
    Task 1: Check which models need retraining

    Returns list of (ticker, horizon) tuples
    """
    print("📋 Checking which models need retraining...")

    from scripts.retrain_scheduler import RetrainingScheduler

    scheduler = RetrainingScheduler()
    to_retrain = []

    for ticker in VN30_STOCKS:
        for horizon in HORIZONS:
            should_retrain, reason = scheduler.should_retrain(
                ticker, horizon,
                strategy='time',
                retrain_interval_days=7  # Weekly
            )

            if should_retrain:
                to_retrain.append((ticker, horizon))
                print(f"✅ {ticker} ({horizon}): {reason}")
            else:
                print(f"⏭️  {ticker} ({horizon}): {reason}")

    # Push to XCom for next task
    context['ti'].xcom_push(key='to_retrain', value=to_retrain)

    print(f"\n📊 Total models to retrain: {len(to_retrain)}")
    return to_retrain


def fetch_training_data(**context):
    """
    Task 2: Fetch latest data for models that need retraining
    """
    to_retrain = context['ti'].xcom_pull(key='to_retrain')

    if not to_retrain:
        print("✅ No models need retraining")
        return {}

    print(f"📊 Fetching data for {len(to_retrain)} models...")

    # Get unique tickers
    tickers = list(set([ticker for ticker, _ in to_retrain]))

    # Fetch data from database
    # TODO: Replace with actual database query
    from database.connection import get_connection
    import pandas as pd

    conn = get_connection()
    data_by_ticker = {}

    for ticker in tickers:
        query = f"""
        SELECT time, open, high, low, close, volume
        FROM stock_prices
        WHERE ticker = '{ticker}'
        ORDER BY time DESC
        LIMIT 1500  -- Get ~4 years of data
        """

        df = pd.read_sql(query, conn)
        df = df.sort_values('time')
        df.set_index('time', inplace=True)

        data_by_ticker[ticker] = df
        print(f"✅ {ticker}: {len(df)} days")

    # Push to XCom
    context['ti'].xcom_push(key='training_data', value=data_by_ticker)

    return data_by_ticker


def retrain_models(**context):
    """
    Task 3: Retrain models
    """
    to_retrain = context['ti'].xcom_pull(key='to_retrain')
    training_data = context['ti'].xcom_pull(key='training_data')

    if not to_retrain:
        print("✅ No models to retrain")
        return []

    print(f"🏋️ Retraining {len(to_retrain)} models...")

    from scripts.retrain_scheduler import RetrainingScheduler
    scheduler = RetrainingScheduler()

    results = []

    for ticker, horizon in to_retrain:
        print(f"\n{'='*80}")
        print(f"🔄 Retraining: {ticker} ({horizon})")
        print(f"{'='*80}")

        try:
            data = training_data[ticker]

            result = scheduler.retrain_model(
                ticker=ticker,
                horizon=horizon,
                data=data,
                compare_with_old=True
            )

            results.append(result)

            if result['status'] == 'deployed':
                print(f"✅ {ticker} ({horizon}): Deployed")
            else:
                print(f"⚠️ {ticker} ({horizon}): {result['status']}")

        except Exception as e:
            print(f"❌ {ticker} ({horizon}): ERROR - {str(e)}")
            results.append({
                'ticker': ticker,
                'horizon': horizon,
                'status': 'error',
                'error': str(e)
            })

    # Push results to XCom
    context['ti'].xcom_push(key='retrain_results', value=results)

    return results


def send_notification(**context):
    """
    Task 4: Send notification about retraining results
    """
    results = context['ti'].xcom_pull(key='retrain_results')

    if not results:
        print("✅ No retraining performed")
        return

    # Count results by status
    deployed = sum(1 for r in results if r['status'] == 'deployed')
    candidate = sum(1 for r in results if r['status'] == 'candidate')
    errors = sum(1 for r in results if r['status'] == 'error')

    # Create summary message
    message = f"""
📊 **Ensemble Model Retraining Report**
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Summary:**
- Total models processed: {len(results)}
- ✅ Deployed: {deployed}
- ⚠️ Candidates (not deployed): {candidate}
- ❌ Errors: {errors}

**Details:**
"""

    for r in results:
        status_emoji = {
            'deployed': '✅',
            'candidate': '⚠️',
            'error': '❌'
        }.get(r['status'], '❓')

        ticker = r['ticker']
        horizon = r['horizon']
        status = r['status']

        if 'new_mape' in r:
            message += f"\n{status_emoji} {ticker} ({horizon}): {status} - MAPE {r['new_mape']:.3f}%"
            if 'improvement' in r:
                message += f" (improved {r['improvement']:+.3f}%)"
        else:
            message += f"\n{status_emoji} {ticker} ({horizon}): {status}"

    print(message)

    # TODO: Send to Discord/Telegram/Email
    # send_discord_message(message)

    return message


# Default DAG arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define DAG
dag = DAG(
    'retrain_ensemble_models',
    default_args=default_args,
    description='Automatic weekly retraining of ensemble models',
    schedule_interval='0 2 * * 1',  # Every Monday at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'prediction', 'ensemble'],
)

# Define tasks
task_check = PythonOperator(
    task_id='check_retraining_needed',
    python_callable=check_retraining_needed,
    provide_context=True,
    dag=dag,
)

task_fetch_data = PythonOperator(
    task_id='fetch_training_data',
    python_callable=fetch_training_data,
    provide_context=True,
    dag=dag,
)

task_retrain = PythonOperator(
    task_id='retrain_models',
    python_callable=retrain_models,
    provide_context=True,
    dag=dag,
)

task_notify = PythonOperator(
    task_id='send_notification',
    python_callable=send_notification,
    provide_context=True,
    dag=dag,
)

# Set task dependencies
task_check >> task_fetch_data >> task_retrain >> task_notify
