# # Use an official Python runtime as a parent image
# FROM python:3.11-slim

# # Set the working directory in the container
# WORKDIR /app

# # Copy the requirements file into the working directory
# COPY requirements.txt .

# # Install any dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the entire project code into the container
# COPY . .

# # Expose port 8000 to the outside world
# EXPOSE 8000

# # Run the Django migrations and collect static files
# # The migrate command will create the db.sqlite3 file if it doesn't exist
# RUN python manage.py migrate
# RUN python manage.py collectstatic --noinput

# # Define the command to run the application
# # Use `python -m gunicorn` to run it as a module
# CMD ["python", "-m", "gunicorn", "phoenix_mart.wsgi:application", "--bind", "0.0.0.0:8000"]



# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment vars to avoid Python writing pyc files and enable unbuffered mode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Run the Django migrations and collect static files
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

# Define the command to run the application
CMD ["python", "-m", "gunicorn", "phoenix_mart.wsgi:application", "--bind", "0.0.0.0:8000"]