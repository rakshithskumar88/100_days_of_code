import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fim-adapter")

app = fastapi.FastAPI()

# Your running pure-CUDA engine
LLAMA_SERVER_URL = "http://127.0.0.1:8888"

@app.get("/{path:path}")
async def catch_all_get(request: Request, path: str):
    logger.info(f"DevoxxGenie sent GET to: /{path}")
    
    # Instantly satisfy any request looking for models
    if "models" in path:
        return JSONResponse({
            "object": "list",
            "data": [{"id": "qwen2.5-coder-3b", "object": "model", "owned_by": "local"}]
        })
        
    return JSONResponse({"status": "alive"})

@app.post("/{path:path}")
async def catch_all_post(request: Request, path: str):
    logger.info(f"DevoxxGenie sent POST to: /{path}")
    payload = await request.json()
    
    # Strip double slashes if any, and route to llama.cpp completions
    target_path = "v1/completions" if "completions" in path else path
    target_url = f"{LLAMA_SERVER_URL}/{target_path}"
    
    async def stream_generator():
        async with httpx.AsyncClient(timeout=10.0) as client:
            req = client.build_request("POST", target_url, json=payload)
            resp = await client.send(req, stream=True)
            async for chunk in resp.aiter_bytes():
                yield chunk

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    logger.info("FIM Adapter running on http://127.0.0.1:8085")
    uvicorn.run(app, host="127.0.0.1", port=8085, log_level="warning")
