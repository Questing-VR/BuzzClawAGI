FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV BRIDGE_STATE_DIR=/data/bridge-state
ENV OPENAGI_URL=http://openagi:43210
ENV POLL_INTERVAL=8
ENV DRY_RUN=0

VOLUME ["/data"]

CMD ["python", "-u", "openagi_to_zeroclaw.py"]
