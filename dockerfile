# use official python runtime
FROM python:3.11-slim

# set environment variables
ENV pythondontwritebytecode=1
ENV pythonunbuffered=1

# set working directory
WORKDIR /app

# install system dependencies (only keep what’s needed at runtime)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

EXPOSE 8000


CMD ["gunicorn", "phoenix_mart.wsgi:application", "--bind", "0.0.0.0:8000"]

