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
from app.api import create_app
from fastapi import Request, HTTPException, Query, WebSocket, WebSocketDisconnect

app = create_app()

@app.get("/")
def read_root():
    """Root endpoint providing a welcome message."""
    return {"message": "GitScape"}

@app.get("/converter")
def get_digest(
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
            # The original clone_repository is now a generator,
            # but for the HTTP endpoint, we consume it without sending progress.
            # This could be made more efficient if needed, but for now,
            # we'll just iterate through it to ensure it completes.
            for _ in converter.clone_repository(repo_url, clone_path, github_token=github_token):
                pass # Consume generator
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
    streaming progress updates to the client.
    """
    await websocket.accept()
    loop = asyncio.get_event_loop() # Get event loop for run_coroutine_threadsafe
    sender_task = None # Initialize sender_task to None

    try:
        repo_url = urllib.parse.unquote(repo_url)  # Decode URL-encoded repo_url
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = os.path.join(tmpdir, "repo")
            await websocket.send_text("progress: Starting repository clone...")
            # Stream clone progress
            for progress_update in converter.clone_repository(repo_url, clone_path, github_token=github_token):
                await websocket.send_text(str(progress_update))
                await asyncio.sleep(0.01) # Small sleep to allow other tasks, and prevent overwhelming the client

            await websocket.send_text("progress: Repository cloned. Starting digest generation...")

            progress_queue = asyncio.Queue()

            def sync_progress_callback(message: str):
                """Callback to put messages onto the asyncio queue from a synchronous thread."""
                try:
                    asyncio.run_coroutine_threadsafe(progress_queue.put(message), loop).result()
                except Exception as e:
                    # Log error if putting to queue fails (e.g., loop closed)
                    print(f"Error in sync_progress_callback putting to queue: {e}")


            # Task to read from queue and send to WebSocket
            async def queue_to_websocket_sender():
                """Reads messages from progress_queue and sends them over WebSocket."""
                while True:
                    message = await progress_queue.get()
                    if message is None: # Sentinel to stop
                        progress_queue.task_done()
                        break
                    try:
                        await websocket.send_text(str(message))
                    except WebSocketDisconnect:
                        print("WebSocket disconnected during send from queue.")
                        progress_queue.task_done() # Ensure task_done is called
                        # Potentially re-raise or handle to stop further processing
                        break
                    except Exception as e:
                        print(f"Error sending message from queue to websocket: {e}")
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

            # Signal the sender to stop and wait for it
            await progress_queue.put(None) # Send sentinel
            await progress_queue.join()    # Wait for all queue items to be processed
            await sender_task              # Ensure sender task itself has completed

            await websocket.send_text(f"digest_complete:{markdown_digest}")

    except WebSocketDisconnect:
        print(f"Client {websocket.client} disconnected")
    except Exception as e:
        error_message = f"error: An unexpected error occurred: {str(e)}"
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                 await websocket.send_text(error_message)
        except Exception as ws_send_error:
            print(f"Error sending error to WebSocket during general exception: {ws_send_error}")
        print(error_message) # Log to server console as well
    finally:
        # Ensure sender_task is cancelled if it's still running and an error occurred
        # before it received the None sentinel.
        if sender_task and not sender_task.done(): # Check if sender_task is not None
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                print("Sender task cancelled.")
            except Exception as e_cancel:
                print(f"Error during sender_task cancellation: {e_cancel}")

        if websocket.client_state == websocket.client_state.CONNECTED:
            await websocket.close()
        print(f"WebSocket connection closed for {websocket.client}")


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
