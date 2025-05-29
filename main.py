"""
Main FastAPI application file for GitScape.
Defines API endpoints for repository analysis and digest generation,
including a standard HTTP endpoint and a WebSocket endpoint for real-time progress.

Author: João Machete
"""
import os
import tempfile
import time
import uvicorn
import converter
from app.api import create_app
from fastapi import Request, HTTPException, Query

app = create_app()

@app.get("/")
def read_root():
    return {"message": "GitScape"}

@app.get("/converter")
def get_digest(
    repo_url: str = Query(..., description="Git repository URL to analyze"),
    github_token: str = Query(None, description="GitHub Personal Access Token for private repos or increased rate limits")
    ):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = os.path.join(tmpdir, "repo")
            converter.clone_repository(repo_url, clone_path, github_token=github_token)
            markdown = converter.generate_markdown_digest(repo_url, clone_path)
        return {"digest": markdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# add middleware which calculates time of the request processing
# and assign it to the response header
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = str(process_time)
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
