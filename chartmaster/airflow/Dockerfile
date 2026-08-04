FROM apache/airflow:2.10.5-python3.10

USER root
RUN useradd --uid 1000 --gid 0 --home-dir /home/dnhs01 --create-home --shell /bin/bash dnhs01

USER airflow
COPY requirements.txt /tmp/chartmaster-requirements.txt
RUN pip install --no-cache-dir -r /tmp/chartmaster-requirements.txt
