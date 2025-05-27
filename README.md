# FastAPI Example for Google Cloud Run

A simple, well-structured FastAPI application designed to run on Google Cloud Run.

## Quick Commands

<!-- dev -->
fastapi dev
or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

<!-- production -->
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

## Docker Commands
docker ps
docker build -t git_scape_api .
docker images
docker run -d -p 8080:8080 --name git_scape_container git_scape_api

docker stop git_scape_container
docker rm git_scape_container
docker rmi git_scape_api

## Features

- RESTful API with CRUD operations
- Interactive API documentation with Swagger UI
- Health check endpoint for monitoring
- Docker containerization for Cloud Run deployment
- Environment variable configuration

## Deployment Notes for Google Cloud Run:

These are general steps you would follow to deploy this application to Google Cloud Run. You'll need `gcloud` CLI installed and configured.

1.  **Enable APIs:**
    * Ensure the Cloud Run API and Artifact Registry API (or Container Registry API) are enabled for your Google Cloud project.
    ```bash
    gcloud services enable run.googleapis.com
    gcloud services enable artifactregistry.googleapis.com
    ```

2.  **Authenticate gcloud:**
    * If you haven't already, authenticate the `gcloud` CLI:
    ```bash
    gcloud auth login
    gcloud auth configure-docker
    ```
    (You might need to specify a region for Docker, e.g., `gcloud auth configure-docker us-central1-docker.pkg.dev`)

3.  **Set Project ID:**
    * Set your current project (replace `YOUR_PROJECT_ID`):
    ```bash
    gcloud config set project YOUR_PROJECT_ID
    ```

4.  **Build the Docker Image:**
    * Navigate to the directory containing `main.py`, `Dockerfile`, and `requirements.txt`.
    * Build the image using Cloud Build (recommended) or locally with Docker.
        * **Using Cloud Build (builds in the cloud and pushes to Artifact Registry):**
            Replace `YOUR_REGION`, `YOUR_PROJECT_ID`, and `YOUR_IMAGE_NAME`.
            ```bash
            gcloud builds submit --tag YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/REPOSITORY_NAME/YOUR_IMAGE_NAME:latest .
            ```
            (If you don't have an Artifact Registry repository, you'll need to create one first: `gcloud artifacts repositories create REPOSITORY_NAME --repository-format=docker --location=YOUR_REGION`)

        * **Building locally with Docker (then push):**
            ```bash
            docker build -t YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/REPOSITORY_NAME/YOUR_IMAGE_NAME:latest .
            docker push YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/REPOSITORY_NAME/YOUR_IMAGE_NAME:latest
            ```

5.  **Deploy to Cloud Run:**
    * Deploy the container image to Cloud Run. Replace placeholders.
    ```bash
    gcloud run deploy YOUR_SERVICE_NAME \
        --image YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/REPOSITORY_NAME/YOUR_IMAGE_NAME:latest \
        --platform managed \
        --region YOUR_DEPLOY_REGION \
        --allow-unauthenticated \
        --project YOUR_PROJECT_ID
    ```
    * `YOUR_SERVICE_NAME`: A name for your Cloud Run service (e.g., `my-fastapi-app`).
    * `YOUR_DEPLOY_REGION`: The region where you want to deploy (e.g., `us-central1`).
    * `--allow-unauthenticated`: Makes the service publicly accessible. Remove this if you want to manage access via IAM.

6.  **Access Your Service:**
    * After deployment, Cloud Run will provide a URL for your service. You can access your FastAPI app at that URL.

**Important Considerations for Cloud Run:**
* **PORT Environment Variable:** Cloud Run sets a `PORT` environment variable that your application must listen on. The `Dockerfile`'s `CMD` handles this by using `${PORT:-8080}`, which means it will use the `PORT` variable if set, or default to `8080` otherwise.
* **Statelessness:** Cloud Run services should be stateless. Any persistent state should be stored in external services like Cloud SQL, Firestore, or Cloud Storage.
* **Concurrency:** Configure concurrency settings based on your application's needs.
* **Logging & Monitoring:** Cloud Run integrates with Cloud Logging and Cloud Monitoring. Standard output (`print` statements, logging libraries) will be captured.