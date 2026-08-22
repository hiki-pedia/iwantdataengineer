FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/chartmaster/src

RUN apt-get update \
    && apt-get install --no-install-recommends -y openssh-client \
    && useradd --uid 1000 --gid 0 --no-create-home --home-dir /home/dnhs01 chartmaster \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/chartmaster

COPY api/requirements.txt /tmp/chartmaster-api-requirements.txt
RUN pip install --no-cache-dir -r /tmp/chartmaster-api-requirements.txt \
    && pip check

CMD ["python", "-m", "uvicorn", "chartmaster.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
