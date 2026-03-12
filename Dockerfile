FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir --trusted-host * --disable-pip-version-check -r requirements.txt

COPY . /app

EXPOSE 9000

CMD ["python", "manage.py", "runserver", "0.0.0.0:9000"]
