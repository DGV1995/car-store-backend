# Car Store Backend

FastAPI backend for the Car Store application.

## Getting Started

1. Ensure Python 3.11+ and [uv](https://docs.astral.sh/uv/) are installed.
2. Sync dependencies:
   ```bash
   uv sync
   ```
3. (Optional) Create the required directories:
   ```bash
   mkdir -p data uploads
   ```
4. Set the Google API key (required for the AI chat agent):
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```
5. Run the server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.

## API Endpoints

| Method | Path                           | Description                              |
|--------|--------------------------------|------------------------------------------|
| GET    | `/health`                      | Health check                             |
| GET    | `/api/cars`                    | List all cars                            |
| POST   | `/api/cars`                    | Create a new car (multipart)             |
| POST   | `/api/chat`                    | Chat with AI car expert (SSE stream)     |
| GET    | `/api/chat/conversations`      | List all conversations (sorted)          |
| GET    | `/api/chat/conversations/{id}` | Get full conversation with all messages  |
| GET    | `/uploads/{fn}`                | Serve uploaded car images                |

## Chat API Usage

### Start a new conversation

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": null, "message": "What cars do you have?"}'
```

### Continue an existing conversation

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "<uuid>", "message": "Show me BMWs under 30000€"}'
```

### List conversations

```bash
curl http://localhost:8000/api/chat/conversations
```

### Get a specific conversation

```bash
curl http://localhost:8000/api/chat/conversations/<uuid>
```

The chat endpoint returns a **Server-Sent Events (SSE)** stream:
- `event: conversation_id` — the conversation UUID
- `event: token` — each chunk of the assistant's reply
- `event: done` — stream complete

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entrypoint
│   ├── models.py         # Pydantic data models (Car + Chat)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── cars.py       # Car API routes
│   │   └── chat.py       # Chat API routes (ADK-powered)
│   └── services/
│       ├── __init__.py
│       ├── file_service.py           # JSON file persistence (cars)
│       ├── conversations_service.py  # JSON file persistence (conversations)
│       └── chat_agent.py             # Google ADK-powered chatbot agent
├── data/
│   ├── .gitkeep
│   ├── cars.json          # Persistent car storage
│   └── conversations.json # Persistent conversation storage (auto-created)
├── uploads/               # Uploaded images directory
├── pyproject.toml
├── .gitignore
└── README.md
```

## Environment Variables

| Variable         | Required | Default            | Description                    |
|------------------|----------|--------------------|--------------------------------|
| `GOOGLE_API_KEY` | Yes*     | —                  | Google AI / Gemini API key     |
| `ADK_MODEL`      | No       | `gemini-2.0-flash` | ADK model identifier           |

*Without `GOOGLE_API_KEY` the chat agent falls back to a built-in rule-based response using `read_cars()` directly.
