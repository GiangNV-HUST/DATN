# airflow.Docker
FROM apache/airflow:2.8.1-python3.11

USER airflow

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Install dependencies 
RUN pip install --no-cache-dir -r /tmp/requirements.txt 

USER airflow

