import os
import tempfile
import time
import uvicorn
from app.api import create_app
from fastapi import Request, HTTPException, Query
from converter import clone_repository, analyze_codebase, generate_markdown

app = create_app()

@app.get("/")
def read_root():
    return {"message": "FastAPI"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/githubDigest")
def get_digest(repo_url: str = Query(..., description="Git repository URL to analyze")):
    """
    Generate a comprehensive markdown summary of a Git repository's codebase. This summary includes file counts, total lines of code, statistics by file extension, and a tree structure of the repository, making it suitable for use with Large Language Models (LLMs).
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = os.path.join(tmpdir, "repo")
            # Clone the repository
            clone_repository(repo_url, clone_path)
            # Analyze the codebase and generate statistics
            file_count, total_lines, extension_stats, file_contents, tree_structure = (
                analyze_codebase(clone_path)
            )
            # Generate markdown digest output
            markdown = generate_markdown(
                repo_url,
                file_count,
                total_lines,
                extension_stats,
                file_contents,
                tree_structure,
            )
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
