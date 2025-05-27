# Dockerfile
# This file describes how to build the Docker image for your FastAPI application.

# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file into the container at /app
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
#    --no-cache-dir: Disables the cache to reduce image size.
#    --upgrade pip: Ensures pip is up-to-date.
#    -r requirements.txt: Installs packages from the requirements file.
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code into the container at /app
COPY . .

# 6. Expose the port the app runs on.
#    Google Cloud Run will automatically detect this, but it's good practice.
#    Cloud Run expects the application to listen on the port defined by the PORT environment variable,
#    which defaults to 8080. Uvicorn will be configured to use this.
EXPOSE 8080

# 7. Define the command to run your application.
#    This command is executed when the container starts.
#    We use Uvicorn to serve the FastAPI application.
#    - "main:app": Refers to the `app` instance in the `main.py` file.
#    - "--host", "0.0.0.0": Makes the server accessible from outside the container.
#    - "--port", "${PORT:-8080}": Uvicorn will listen on the port specified by the
#      PORT environment variable, defaulting to 8080 if PORT is not set.
#      Google Cloud Run sets the PORT environment variable automatically.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
