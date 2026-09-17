# Wayfarer — Travel Planner

A travel planner built with Python, LangGraph, and FastAPI. Give it a trip idea in
plain English, and it looks up flight information and hotel suggestions before
putting together a daily itinerary and estimated budget.

For example:

> Create a 7 day plan for travel from Kochi, Kerala to Copenhagen, Denmark.

You can use the browser interface or run the agent directly from the terminal.

## How it works

The main workflow lives in `backend.py`. It uses a LangGraph `StateGraph` with
four nodes that run in a fixed order:

```text
User query
    |
    v
Flight search -> Hotel search -> Itinerary -> Final response
```

1. **Flight search** passes the query to `tools/flight_tool.py`. The tool extracts
   the route, resolves locations to airport IATA codes, and requests flight
   records from AviationStack.
2. **Hotel search** sends a query to Tavily through `tools/tavily_tool.py`. It
   returns up to five web results with titles, links, and short excerpts.
3. **Itinerary** combines the original request with both search results and asks
   the model to draft a practical plan.
4. **Final response** makes a second model call to organize the draft into a trip
   summary, flights, hotels, daily itinerary, budget, and recommendations.

The first two nodes call search tools directly. The last two use Groq through
`ChatGroq`, configured with `openai/gpt-oss-120b` and a temperature of `0.0`.

Each node reads and updates a shared `TravelState`, which holds the query,
messages, search results, itinerary, and a counter. The field named `llm_calls`
currently increments in all four nodes, so it counts workflow steps rather than
just model calls.

LangGraph saves checkpoints to PostgreSQL using `PostgresSaver`, with a
`thread_id` identifying each run's conversation state. The browser starts a new
thread for every submission. The terminal script uses the fixed ID `test_user`.

## Where the web app fits

`app.py` serves the page and exposes `POST /api/plan`. It validates the input,
calls `run_travel_agent()`, and returns the result without changing the agent's
workflow. The browser renders the answer, including headings, lists, and tables,
and lets you expand the original flight and hotel results.

Agent calls run in FastAPI's thread pool so the web server can keep responding
while a plan is being generated. A lock allows one agent run per server process
at a time because the backend uses a shared database connection. Another request
during that run gets a `503` response and a retry hint.

```text
trip_planner/
├── app.py                  # FastAPI routes and the web-to-agent adapter
├── backend.py              # Graph, state, prompts, model, and checkpoints
├── test.py                 # Interactive terminal entry point
├── tools/
│   ├── flight_tool.py      # Route parsing and AviationStack requests
│   └── tavily_tool.py      # Hotel web search and result formatting
├── templates/
│   └── index.html          # Browser interface
├── static/
│   ├── style.css
│   └── script.js
├── tests/                  # API and flight-tool regression tests
└── requirements.txt
```

## Running locally

Install the dependencies, preferably in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root with your service credentials:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
AVIATIONSTACK_API_KEY=your_aviationstack_key
```

The database must be reachable and the database user must be able to create the
checkpoint tables. The backend sets these up when it is first loaded. It also
adds `sslmode=require` if the database URL does not specify an SSL mode.

Start the web app:

```powershell
python app.py
```

Open [the planner](http://127.0.0.1:8000) or
[the API docs](http://127.0.0.1:8000/docs). The page can load before the agent is
initialized; submitting a trip is what loads the backend and connects to its
services.

For automatic reloads while editing, use `python -m uvicorn app:app --reload`
instead. Run only one server on port 8000. If you get an “address already in use”
error, stop the previous server with `Ctrl+C`, or use another port:

```powershell
python -m uvicorn app:app --port 8001
```

To use the agent without the frontend:

```powershell
python test.py
```

## API

Send a JSON body to `POST /api/plan`:

```json
{
  "user_input": "Create a 7 day plan from Kochi to Copenhagen."
}
```

You can also supply a `thread_id`. The response contains `answer`, `thread_id`,
`flight_results`, `hotel_results`, `itinerary`, and `llm_calls`.

`GET /api/health` checks whether the web server is running. It does not check the
database or external APIs.

## A few limitations

AviationStack supplies flight records, not bookable fares or complete connecting
itineraries. An empty route result does not mean the trip is impossible. Hotel
suggestions come from web search rather than a live room-availability service,
and generated budgets are estimates. Check the details before booking.

The app currently runs locally and has no authentication or booking flow.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The tests cover route resolution, flight-request filters, input validation,
API errors, and overlapping requests. External calls are mocked, so running the
suite does not need API credits or a live database. `test.py` is separate: it
runs the actual agent and does need the configured services.

## Frontend credit

The HTML, CSS, and JavaScript frontend was AI-generated with OpenAI Codex.
