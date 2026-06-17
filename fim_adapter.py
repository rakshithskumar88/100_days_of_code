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
    if "models" in path:
        return JSONResponse(
            {
                "object": "list",
                "data": [
                    {"id": "qwen2.5-coder-3b", "object": "model", "owned_by": "local"}
                ],
            }
        )
    return JSONResponse({"status": "alive"})


@app.post("/{path:path}")
async def catch_all_post(request: Request, path: str):
    payload = await request.json()

    target_path = "v1/completions" if "completions" in path else path
    target_url = f"{LLAMA_SERVER_URL}/{target_path}"

    if "completions" in target_path:
        prefix = payload.get("prompt", "")
        suffix = payload.get("suffix", "")

        # 1. GOLDEN FIM FORMATTING
        if suffix:
            payload["prompt"] = (
                f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"
            )
            payload.pop("suffix", None)

        # 2. DYNAMIC BRAKES
        existing_stops = payload.get("stop", [])
        if not isinstance(existing_stops, list):
            existing_stops = [existing_stops] if existing_stops else []

        existing_stops.extend(
            [
                "\ndef ",
                "\nclass ",
                "<|file_separator|>",
                "<|endoftext|>",
                "<|im_end|>",
                "<|fim_pad|>",
            ]
        )

        if suffix:
            for line in suffix.split("\n"):
                if len(line.strip()) > 2:
                    existing_stops.append(line)
                    existing_stops.append(line.strip())
                    break

        payload["stop"] = list(set(existing_stops))
        payload["temperature"] = 0.1

    async def stream_generator():
        # Pure, unadulterated passthrough. No more whitespace fighting.
        async with httpx.AsyncClient(timeout=30.0) as client:
            req = client.build_request("POST", target_url, json=payload)
            resp = await client.send(req, stream=True)
            async for chunk in resp.aiter_bytes():
                yield chunk

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    logger.info("FIM Adapter running on http://127.0.0.1:8085")
    uvicorn.run(app, host="127.0.0.1", port=8085, log_level="warning")
