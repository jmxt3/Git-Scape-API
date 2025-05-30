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
import converter # Assuming converter.py is in the same directory or accessible via PYTHONPATH
import asyncio # Required for WebSocket and async operations
import urllib.parse # For decoding URL-encoded parameters
import json
import logging
from app.api import create_app
from fastapi import Request, HTTPException, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.responses import FileResponse, HTMLResponse
# slowapi imports
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

# SlowAPI setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Custom handler for RateLimitExceeded
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )

@app.head("/")
async def head_root() -> HTMLResponse:
    """
    Respond to HTTP HEAD requests for the root URL.

    Mirrors the headers and status code of the index page.

    Returns
    -------
    HTMLResponse
        An empty HTML response with appropriate headers.
    """
    return HTMLResponse(content=None, headers={"content-type": "text/html; charset=utf-8"})

@app.get("/converter")
@limiter.limit("5/minute")
def get_digest(request: Request,
    repo_url: str = Query(..., description="Git repository URL to analyze"),
    github_token: str = Query(None, description="GitHub Personal Access Token for private repos or increased rate limits")
    ):
    """
    HTTP endpoint to clone a Git repository and generate a Markdown digest.
    This is a blocking operation.
    """
    try:
        repo_url = urllib.parse.unquote(repo_url)  # Decode URL-encoded repo_url
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = os.path.join(tmpdir, "repo")
            # Call clone_repository as a regular function (not iterable)
            converter.clone_repository(repo_url, clone_path, github_token=github_token)
            markdown = converter.generate_markdown_digest(repo_url, clone_path)
        return {"digest": markdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/converter")
async def websocket_converter(
    websocket: WebSocket,
    repo_url: str = Query(..., description="Git repository URL to analyze"),
    github_token: str = Query(None, description="GitHub Personal Access Token for private repos or increased rate limits")
):
    """
    WebSocket endpoint to clone a Git repository and generate a Markdown digest,
    streaming progress updates to the client as JSON with percentage.
    """
    await websocket.accept()
    loop = asyncio.get_event_loop() # Get event loop for run_coroutine_threadsafe
    sender_task = None # Initialize sender_task to None

    try:
        repo_url = urllib.parse.unquote(repo_url)  # Decode URL-encoded repo_url
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = os.path.join(tmpdir, "repo")
            await websocket.send_text(json.dumps({"type": "progress", "message": "Starting repository clone...", "percentage": 0}))
            # Call clone_repository as a regular function (not iterable)
            converter.clone_repository(repo_url, clone_path, github_token=github_token)
            await websocket.send_text(json.dumps({"type": "progress", "message": "Repository cloned. Starting digest generation...", "percentage": 10}))

            progress_queue = asyncio.Queue()

            def sync_progress_callback(message: str, percentage: int):
                try:
                    asyncio.run_coroutine_threadsafe(progress_queue.put({"type": "progress", "message": message, "percentage": percentage}), loop).result()
                except Exception as e:
                    logger.error(f"Error in sync_progress_callback putting to queue: {e}")

            async def queue_to_websocket_sender():
                while True:
                    item = await progress_queue.get()
                    if item is None:
                        progress_queue.task_done()
                        break
                    try:
                        await websocket.send_text(json.dumps(item))
                    except WebSocketDisconnect:
                        logger.info("WebSocket disconnected during send from queue.")
                        progress_queue.task_done()
                        break
                    except Exception as e:
                        logger.error(f"Error sending message from queue to websocket: {e}")
                    progress_queue.task_done()
                    await asyncio.sleep(0.01)

            sender_task = asyncio.create_task(queue_to_websocket_sender())

            markdown_digest = await loop.run_in_executor(
                None, # Uses default ThreadPoolExecutor
                converter.generate_markdown_digest,
                repo_url,
                clone_path,
                sync_progress_callback
            )

            await progress_queue.put(None)
            await progress_queue.join()
            await sender_task

            await websocket.send_text(json.dumps({"type": "digest_complete", "digest": markdown_digest, "percentage": 100}))

    except WebSocketDisconnect:
        logger.info(f"Client {websocket.client} disconnected")
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                await websocket.send_text(json.dumps({"type": "error", "message": error_message, "percentage": 100}))
        except Exception as ws_send_error:
            logger.error(f"Error sending error to WebSocket during general exception: {ws_send_error}")
        logger.error(error_message)
    finally:
        if sender_task and not sender_task.done():
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                logger.info("Sender task cancelled.")
            except Exception as e_cancel:
                logger.error(f"Error during sender_task cancellation: {e_cancel}")
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except RuntimeError as close_err:
                logger.warning(f"WebSocket close error (already closed?): {close_err}")
        logger.info(f"WebSocket connection closed for {websocket.client}")


# add middleware which calculates time of the request processing
# and assign it to the response header
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add X-Process-Time-Sec header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = str(process_time)
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
