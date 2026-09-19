# Wayfarer — Travel Planner

A travel planner built with Python, LangGraph, FastAPI, and the Model Context
Protocol (MCP). Give it a trip idea in plain English, and it looks up flight,
hotel, and weather information before putting together a daily itinerary and
estimated budget.

For example:

> Create a 7 day plan for travel from Kochi, Kerala to Copenhagen, Denmark.

You can use the browser interface or run the agent directly from the terminal.

## How it works

The main workflow lives in `backend.py`. It uses a LangGraph `StateGraph` with
five nodes that run in a fixed order:

```text
User query
    |
    v
Flight search -> Hotel search -> Weather -> Itinerary -> Final response
```

1. **Flight search** passes the query through `mcp_client.py` to the AviationStack
   MCP server and asks the model to summarize the available airport and airline
   data.
2. **Hotel search** sends a query to the remote Tavily MCP server. It returns web
   search results with titles, links, and short excerpts.
3. **Weather** extracts the destination and calls the custom weather MCP server
   for current conditions and a forecast.
4. **Itinerary** combines the original request with the flight, hotel, and
   weather results and asks the model to draft a practical plan.
5. **Final response** makes a second model call to organize the draft into a trip
   summary, flights, hotels, weather, daily itinerary, budget, and recommendations.

MCP tools are loaded and invoked through `mcp_client.py` using
`MultiServerMCPClient`. The application currently demonstrates different MCP
server arrangements:

| Server | Type | Connection | Purpose |
| --- | --- | --- | --- |
| Tavily | Remote MCP server | Streamable HTTP | Hotel and web search |
| AviationStack | Local MCP server | stdio through `uvx` | Airport and airline data |
| Weather | Custom local MCP server | stdio through Python | Current weather and forecasts |

The custom server is implemented in `custom_weather_mcp.py` with FastMCP and
calls the OpenWeather API. This shows that MCP servers can be hosted remotely,
run locally from an installed package, or built in the project for a specific
API and workflow. The model calls use Groq through `ChatGroq`, configured with
`openai/gpt-oss-120b` and a temperature of `0.0`.

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
│   └── flight_tool.py      # Legacy route parsing and flight helpers
├── mcp_client.py           # Remote and local MCP client configuration
├── custom_weather_mcp.py   # Custom FastMCP server for OpenWeather
├── mcp_client_test.py      # MCP connectivity/tool inspection script
├── templates/
│   └── index.html          # Browser interface
├── static/
│   ├── style.css
│   └── script.js
├── tests/                  # API and flight-tool regression tests
├── Dockerfile              # Container image used locally and on Render
├── .dockerignore           # Files excluded from Docker's build context
├── render.yaml             # Render web service configuration
├── .github/workflows/ci.yml # Container build, tests, and HTTP checks
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
OPENWEATHER_API_KEY=your_openweather_key
```

The MCP client also expects `uvx` to be available for the local AviationStack
server. The custom weather MCP server currently uses the Python executable and
absolute script path configured in `mcp_client.py`; update those values for your
own machine before running the application.

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

## Running with Docker

With Docker running, build the image from the project root:

```powershell
docker build -t wayfarer .
docker run --rm --name wayfarer -p 127.0.0.1:8000:10000 --env-file .env wayfarer
```

Open [the planner](http://127.0.0.1:8000). If a local Python server is already
using port 8000, stop it first or change the mapping to `127.0.0.1:8001:10000`.
Stop the container with `docker stop wayfarer` from another terminal.

The image runs Python 3.13 as a non-root user. Uvicorn listens on `0.0.0.0` and
uses the `PORT` environment variable, defaulting to `10000`. It runs one worker
to match the backend's shared database connection. The agent code is the same
whether you start it locally or in a container.

`.gitignore` keeps local credentials and generated files out of Git.
`.dockerignore` also excludes them from Docker's build context. The Dockerfile
copies only runtime files, so `.env` is never baked into the image. Supply
credentials at runtime with `--env-file` locally or Render's environment settings.
PostgreSQL stays outside the container; checkpoints survive container replacements.

## Hosting on Render

Render builds and runs the container in its own cloud directly from this GitHub
repository. You do not need Docker installed on your computer, a container
registry, or a locally built image.

1. Push these files to GitHub. The `Dockerfile` must be included in the repository.
2. Open the [Render dashboard](https://dashboard.render.com/) and choose
   **New → Web Service**.
3. Connect your GitHub account and select the repository. You can also paste a
   public GitHub repository URL, but that option requires manual redeployments.
4. Use these settings:

   | Setting | Value |
   | --- | --- |
   | Language / Runtime | Docker |
   | Branch | The branch containing this project, usually `main` |
   | Root Directory | Leave blank if `Dockerfile` is at the repository root |
   | Dockerfile Path | `./Dockerfile` |
   | Docker Build Context | `.` |
   | Docker Command | Leave blank; the Dockerfile supplies it |
   | Health Check Path | `/api/health` |
   | Auto-Deploy | On Commit, when using a connected GitHub account |

   If the project is in a repository subfolder, set Root Directory to that folder.
5. Add these environment variables in Render:

   | Variable | Value to supply |
   | --- | --- |
   | `DATABASE_URL` | Your reachable PostgreSQL connection string |
   | `GROQ_API_KEY` | Your Groq API key |
   | `TAVILY_API_KEY` | Your Tavily API key |
   | `AVIATIONSTACK_API_KEY` | Your AviationStack API key |

6. Choose an instance type and click **Deploy Web Service**. Render installs the
   dependencies, builds the image, and starts the app. Open its `onrender.com`
   URL once the deployment is live.

The GitHub link supplies the code; the environment variables supply the private
configuration. Render cannot read your local `.env`. Use your existing database
or create one separately. No database is included in the application container.
See [Render's Docker guide](https://render.com/docs/docker).

### Optional: import the settings with a Blueprint

To have Render read the service settings from a file, choose **New → Blueprint**
instead and select the connected repository. The included `render.yaml` defines
the Docker runtime, health check, free web-service plan, and automatic deployments.
Render prompts for the four environment variables. Review the plan before
creating the service. `render.yaml` is used by the Blueprint flow; it is not
automatically applied when you create a regular Web Service.

### Automatic builds and deployments

With a connected GitHub account and **On Commit** enabled, Render rebuilds and
redeploys whenever you push or merge to the linked branch:

```text
Push to GitHub -> Render builds the Dockerfile -> Health check -> Updated website
```

The Blueprint also defaults to deployment on commit, so GitHub Actions is not a
prerequisite for deployment. The included CI workflow independently builds and
tests the container on GitHub. If you want passing tests to be required before
release, select **After CI Checks Pass** in Render. For a Blueprint-managed
service, change `autoDeployTrigger` from `commit` to `checksPass` in `render.yaml`.

Pasting a public repository URL works for the initial deployment, but Render
requires a connected Git provider for automatic deployments. No deploy hook or
Render API key is needed in GitHub.
See [Render's auto-deploy documentation](https://render.com/docs/deploys).

The health check confirms that FastAPI is responding. Submit a real trip after
deployment to check the database and external API connections too.

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

The app has no authentication or booking flow. Anyone who can access a public
deployment can submit a trip and use the configured API services.

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
