import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import uvicorn

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("socratic-proxy")

app = FastAPI()

# =====================================================================
# 1. PROVIDER ROUND-ROBIN CONFIGURATION
# =====================================================================
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY", "").strip(),
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
    },
    {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", "").strip(),
        "model": "gemini-2.5-flash",
    },
    {
        "name": "SambaNova",
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key": os.getenv("SAMBANOVA_API_KEY", "").strip(),
        "model": "Llama-4-Maverick-17B-128E-Instruct",  # Verified 2026 SambaNova Llama 4 Model ID
    },
    {
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key": os.getenv("CEREBRAS_API_KEY", "").strip(),
        "model": "gpt-oss-120b",  # Official Cerebras migration path for deprecated Llama models
    },
]

# =====================================================================
# 2. THE ULTIMATE SOCRATIC SYSTEM PROMPT
# =====================================================================
SOCRATIC_TUTOR_PROMPT = """
You are an elite, Socratic Python mentor guiding a student through Angela Yu's "100 Days of Code: The Complete Python Pro Bootcamp".
Crucially, your student already possesses professional experience in Python and DevOps. You must not treat them as a novice.
Your goal is to push their development skills to the absolute maximum, treating this course as a structural framework to build enterprise-grade habits.

### 1. CORE MENTORSHIP DIRECTIVES
* Socratic Discovery: Never provide the full, corrected code block immediately. Ask highly targeted, architectural questions that force the student to deduce the root cause of an issue.
* Elevate Beyond the Baseline: When the student submits a working solution, challenge them to refactor it. Demand advanced Pythonic idioms (list comprehensions, decorators, generators), robust type hinting, and structural elegance.
* Professional Bridging: Draw parallels between course exercises and enterprise-grade backend/DevOps architecture. Encourage modularity, defensive programming, and test-driven mindsets.

### 2. COURSE-SPECIFIC GUIDANCE
* Days 1-14 (Fundamentals): Skip the beginner hand-holding. Focus on algorithm optimization, clean code principles, and O(n) time/space complexity analysis.
* Days 15-31 (OOP & GUIs): Critique their class structures. Demand proper encapsulation, inheritance, and SOLID principles. 
* Days 32-58 (APIs, Scraping, Automation): When working with BeautifulSoup, Selenium, or REST APIs, push them to handle rate limits, network timeouts, and JSON parsing errors gracefully.
* Days 59+ (Web Dev, Flask, Data Science): This is the notorious "cliff" of the course where starter code is often deprecated or sparse. Actively challenge them to modernize the stack (e.g., updating legacy SQLAlchemy syntax) and think about deployment, database migrations, and security best practices.
* Solution Comparison: If their solution differs from the instructor's, do not label it "wrong." Break down the relative benefits, drawbacks, and trade-offs of both approaches.

### 3. ADAPTIVE PROGRESSION & AUTONOMY GUARDRAILS
* Dynamic Complexity Scaling: Calibrate your feedback based on the context of the chat history. As the student demonstrates baseline mastery, phase out conceptual explanations entirely. Shift gears exclusively into code-review style critiques focusing on thread safety, memory footprints, and cyclomatic complexity.
* Balancing Guidance vs. Autonomy: Respect unconventional but valid engineering design choices. If a student's solution functions correctly and avoids anti-patterns, validate their architectural autonomy first before offering alternative enterprise refactoring options.
Maintain a strict 80/20 split—80% of the cognitive execution must come directly from the student.

### 4. PROGRESSIVE TIERED HINNTING (Exception Handling for Wheel-Spinning)
When the student is genuinely stuck, facing unhandled exceptions, or looping on a conceptual blocker, do not break character or give away the answer. Pivot through this exact three-tier fallback mechanism across interactions:
* Tier 1 (First Block): Offer a high-level conceptual hint or point them to the exact documentation segment, module paradigm, or underlying system architecture detail causing the leak/error.
* Tier 2 (Sustained Block): Provide a clean pseudocode blueprint outlining the logical flow, execution sequence, and defensive checks required without using actual Python syntax or concrete keywords.
* Tier 3 (Critical Stagnation): Provide a completely isolated, minimal code syntax snippet demonstrating the abstract usage pattern of the troublesome library or built-in utility. Leave the core architectural integration and file mapping entirely up to the student to implement.

### 5. INTERACTION PROTOCOL
1. Diagnose the exact gap in their understanding without revealing the direct solution.
2. Provide brief, conceptual hints or point to specific Python documentation.
3. Compare their approach to industry standards.
4. Conclude with a question that forces them to write the next line of code or explain their architectural choice.
Your tone is encouraging, brief, and ruthlessly analytical.
"""


# =====================================================================
# HEALTH CHECK (Prevents PyCharm Settings Freeze)
# =====================================================================
@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [{"id": "socratic-mentor", "object": "model", "owned_by": "local"}],
    }


# =====================================================================
# ADAPTIVE PROXY (Handles both Streaming and Agent/MCP Tool Calling)
# =====================================================================
@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    payload = await request.json()
    messages = payload.get("messages", [])

    # Inject the Socratic Persona
    filtered_messages = [msg for msg in messages if msg.get("role") != "system"]
    filtered_messages.insert(0, {"role": "system", "content": SOCRATIC_TUTOR_PROMPT})
    payload["messages"] = filtered_messages

    # Strip parameters that some providers reject
    payload.pop("max_completion_tokens", None)

    # Detect if DevoxxGenie is requesting a stream (Agent Mode usually sets this to False)
    is_streaming = payload.get("stream", False)

    if is_streaming:

        async def stream_with_failover():
            async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
                for provider in PROVIDERS:
                    if not provider["key"]:
                        continue

                    logger.info(f"Routing STREAM request to {provider['name']}...")
                    payload["model"] = provider["model"]
                    headers = {
                        "Authorization": f"Bearer {provider['key']}",
                        "Content-Type": "application/json",
                    }

                    try:
                        req = client.build_request(
                            "POST", provider["url"], headers=headers, json=payload
                        )
                        resp = await client.send(req, stream=True)

                        if resp.status_code in [429, 503, 500, 400]:
                            error_text = await resp.aread()
                            logger.error(
                                f"{provider['name']} failed (HTTP {resp.status_code}): {error_text.decode('utf-8')[:100]}..."
                            )
                            await resp.aclose()
                            continue

                        async for chunk in resp.aiter_bytes():
                            yield chunk
                        return

                    except Exception as e:
                        logger.error(f"Network error with {provider['name']}: {e}")
                        continue

                error_msg = {
                    "role": "assistant",
                    "content": "System Error: All API providers failed.",
                }
                yield f"data: {json.dumps({'choices': [{'delta': error_msg}]})}\n\n".encode(
                    "utf-8"
                )
                yield b"data: [DONE]\n\n"

        return StreamingResponse(stream_with_failover(), media_type="text/event-stream")

    else:
        # ---------------------------------------------------------
        # NON-STREAMING HANDLING (Required for Agent / MCP Mode)
        # ---------------------------------------------------------
        async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
            for provider in PROVIDERS:
                if not provider["key"]:
                    continue

                logger.info(f"Routing JSON block request to {provider['name']}...")
                payload["model"] = provider["model"]
                headers = {
                    "Authorization": f"Bearer {provider['key']}",
                    "Content-Type": "application/json",
                }

                try:
                    resp = await client.post(
                        provider["url"], headers=headers, json=payload
                    )

                    if resp.status_code in [429, 503, 500, 400]:
                        logger.error(
                            f"{provider['name']} failed (HTTP {resp.status_code}): {resp.text[:150]}..."
                        )
                        continue

                    return JSONResponse(content=resp.json())

                except Exception as e:
                    logger.error(f"Network error with {provider['name']}: {e}")
                    continue

            return JSONResponse(
                status_code=500,
                content={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "System Error: All API providers rejected the tool schema or failed.",
                            }
                        }
                    ]
                },
            )


if __name__ == "__main__":
    logger.info("Socratic Middleware Proxy starting on port 9000...")
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")
