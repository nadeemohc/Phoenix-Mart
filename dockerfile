# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Run the Django migrations and collect static files
# The migrate command will create the db.sqlite3 file if it doesn't exist
RUN python manage.py migrate
RUN python manage.py collectstatic --noinput

# Define the command to run the application
# Use `python -m gunicorn` to run it as a module
CMD ["python", "-m", "gunicorn", "phoenix_mart.wsgi:application", "--bind", "0.0.0.0:8000"]
