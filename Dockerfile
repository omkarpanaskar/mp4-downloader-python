FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	VIRTUAL_ENV=/opt/venv \
	PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
	&& python -m pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .
COPY templates ./templates
RUN mkdir -p downloads

EXPOSE 5000
VOLUME ["/app/downloads"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "0", "app:app"]
