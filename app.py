"""HTTP and browser interface for the existing, unmodified travel agent."""
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Wayfarer Travel Planner", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
# The agent owns one shared PostgreSQL connection. Serialize access per process.
agent_lock = Lock()


class PlanRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    user_input: str = Field(min_length=3, max_length=4000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)


def run_agent(user_input: str, thread_id: str | None):
    # Lazy loading keeps the UI available if agent credentials/services are down.
    try:
        from backend import run_travel_agent
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The travel agent could not start. Check its dependencies, .env settings, and database connection.",
        ) from None
    return run_travel_agent(user_input=user_input, thread_id=thread_id)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
def health():
    """Web-server liveness; external agent services are checked on submission."""
    return {"status": "ok"}


@app.post("/api/plan")
def create_plan(payload: PlanRequest):
    # A normal def runs in FastAPI's thread pool, keeping the UI responsive.
    if not agent_lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Another trip is being planned. Please try again shortly.", headers={"Retry-After": "10"})
    try:
        return run_agent(payload.user_input, payload.thread_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="The travel agent could not finish this trip. Please try again, or check the agent's service connections.") from None
    finally:
        agent_lock.release()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
