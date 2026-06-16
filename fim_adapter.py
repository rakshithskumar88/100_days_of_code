import fastapi
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fim-adapter")

app = fastapi.FastAPI(title="Phase 1: FIM Adapter")

# Your pure-CUDA llama.cpp engine
LLAMA_SERVER_URL = "http://127.0.0.1:8888"

@app.get("/api/v1/models")
@app.get("/v1/models")
async def mock_lmstudio_models():
    """Spoof the LM Studio model endpoint so DevoxxGenie populates the dropdown."""
    logger.info("DevoxxGenie requested models. Spoofing LM Studio response...")
    return JSONResponse({
        "data": [
            {
                "id": "qwen2.5-coder-3b",
                "object": "model",
                "owned_by": "local"
            }
        ],
        "object": "list"
    })

@app.post("/v1/completions")
async def forward_fim(request: Request):
    """Intercept DevoxxGenie's FIM request and route it to llama.cpp."""
    payload = await request.json()
    logger.info("Routing FIM autocomplete request to local CUDA engine...")
    
    async def stream_generator():
        async with httpx.AsyncClient(timeout=10.0) as client:
            req = client.build_request("POST", f"{LLAMA_SERVER_URL}/v1/completions", json=payload)
            resp = await client.send(req, stream=True)
            async for chunk in resp.aiter_bytes():
                yield chunk

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    # Running the FIM Adapter on port 8080
    logger.info("FIM Adapter running on http://127.0.0.1:8085")
    uvicorn.run(app, host="127.0.0.1", port=8085, log_level="warning")
