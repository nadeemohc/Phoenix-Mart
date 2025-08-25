# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment vars to avoid Python writing pyc files and enable unbuffered mode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2 and Django
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Default command: run Gunicorn
CMD ["gunicorn", "phoenix_mart.wsgi:application", "--bind", "0.0.0.0:8000"]

