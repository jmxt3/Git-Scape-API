import os
import time
import uvicorn
from app.api import create_app
from fastapi import FastAPI, Request

app = create_app()

@app.get("/")
def read_root():
    return {"message": "Hello World! This is a FastAPI app running on Google Cloud Run."}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    """
    Endpoint to retrieve an item by its ID, with an optional query parameter.
    Example: /items/5?q=somequery
    """
    response = {"item_id": item_id}
    if q:
        response["q"] = q
    return response

@app.get("/health2")
def health_check():
    return {"status": "healthy"}

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
