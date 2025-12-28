# LLM Service

Production-ready LLM conversation service with memory persistence, streaming responses, and multi-session support.

## Architecture Overview

```mermaid
graph TB
    subgraph Client Layer
        WEB[Web Browser]
        API[API Client]
    end

    subgraph Application Layer
        FASTAPI[FastAPI Application]

        subgraph Modules
            LANGCHAIN[LangChain Module]
            WEBMOD[Web Module]
        end
    end

    subgraph Service Layer
        AGENT[Conversation Agent]
        SESSION[Session Service]
        AUTH[Auth Service]
        CHECKPOINTER[Checkpointer Factory]
    end

    subgraph Data Layer
        MONGO[(MongoDB)]
        OPENAI[OpenAI API]
    end

    WEB --> FASTAPI
    API --> FASTAPI

    FASTAPI --> LANGCHAIN
    FASTAPI --> WEBMOD

    LANGCHAIN --> AGENT
    LANGCHAIN --> SESSION
    LANGCHAIN --> CHECKPOINTER

    WEBMOD --> AUTH
    WEBMOD --> SESSION

    AGENT --> OPENAI
    AGENT --> CHECKPOINTER

    SESSION --> MONGO
    AUTH --> MONGO
    CHECKPOINTER --> MONGO
```

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI
    participant S as SessionService
    participant A as ConversationAgent
    participant M as MongoDB
    participant O as OpenAI

    C->>F: POST /conversation
    F->>S: Get/Create Session
    S->>M: Query/Insert Session
    M-->>S: Session Data
    S-->>F: Session Response

    F->>A: Stream Message
    A->>M: Load Checkpoint
    M-->>A: Conversation State

    A->>O: Chat Completion
    O-->>A: Stream Chunks

    loop For each chunk
        A-->>F: Yield Chunk
        F-->>C: SSE Event
    end

    A->>M: Save Checkpoint
    F-->>C: Done Event
```

## Data Model

```mermaid
erDiagram
    USERS {
        string user_id PK
        string name
        string email UK
        string password
        datetime created_at
        datetime updated_at
    }

    SESSIONS {
        string session_id PK
        string thread_id UK
        string user_id FK
        string name
        datetime created_at
        datetime updated_at
    }

    AUTH_SESSIONS {
        string token PK
        string user_id FK
        datetime created_at
        datetime expires_at
    }

    CHECKPOINTS {
        string thread_id PK
        string checkpoint_id
        json channel_values
        json metadata
        datetime ts_created
    }

    USERS ||--o{ SESSIONS : owns
    USERS ||--o{ AUTH_SESSIONS : has
    SESSIONS ||--|| CHECKPOINTS : maps_to
```

## Module Structure

```mermaid
graph LR
    subgraph Config
        SETTINGS[settings.py]
    end

    subgraph Shared
        MODELS[Models]
        PERSISTENCE[Persistence]
        SERVICES[Services]
    end

    subgraph Modules
        subgraph LangChain
            AGENTS[Agents]
            TOOLS[Tools]
            LC_SERVICES[Services]
            LC_HANDLERS[HTTP Handlers]
        end

        subgraph Web
            WEB_SERVICES[Services]
            WEB_HANDLERS[HTTP Handlers]
            TEMPLATES[Templates]
        end
    end

    SETTINGS --> SHARED
    SHARED --> Modules

    AGENTS --> LC_SERVICES
    LC_HANDLERS --> AGENTS
    LC_HANDLERS --> LC_SERVICES

    WEB_HANDLERS --> WEB_SERVICES
    WEB_HANDLERS --> TEMPLATES
```

## CI/CD Pipeline

```mermaid
graph LR
    subgraph CI
        LINT[Lint]
        UNIT[Unit Tests]
        INT[Integration Tests]
        TC[Testcontainers]
        SEC[Security Scan]
    end

    subgraph CD
        BUILD[Build Image]
        STAGING[Deploy Staging]
        PROD[Deploy Production]
    end

    LINT --> BUILD
    UNIT --> BUILD
    INT --> BUILD
    TC --> BUILD
    SEC --> BUILD

    BUILD --> STAGING
    STAGING --> PROD
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- uv package manager

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd llm-service-boilerplate
```

### Step 2: Install Dependencies

```bash
uv sync
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
OPENAI_API_KEY=your_openai_api_key
MONGO_URI=mongodb://admin:admin@localhost:27017/?authSource=admin
MONGO_DB=langchain
JWT_SECRET=your_secure_secret
```

### Step 4: Start MongoDB

```bash
docker-compose up -d
```

### Step 5: Run Application

```bash
uv run python main.py
```

Access the application at `http://localhost:8000`

## Testing

### Run All Tests

```bash
uv sync --all-extras
uv run pytest
```

### Run Unit Tests Only

```bash
uv run pytest tests/unit -m unit
```

### Run Integration Tests

```bash
uv run pytest tests/integration -m integration
```

### Run with Coverage

```bash
uv run pytest --cov=config --cov=shared --cov=modules --cov-report=html
```

## API Endpoints

### Conversation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/conversation` | Send message (streaming/non-streaming) |
| POST | `/conversation/session` | Create new session |
| GET | `/conversation/session/{id}` | Get session details |
| GET | `/conversation/sessions/user/{id}` | List user sessions |
| PATCH | `/conversation/session/{id}` | Update session name |
| DELETE | `/conversation/session/{id}` | Delete session |
| GET | `/conversation/session/{id}/history` | Get chat history |

### Web Interface

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/web/` | Home page |
| GET | `/web/login` | Login page |
| GET | `/web/register` | Registration page |
| GET | `/web/chat` | Chat interface |
| POST | `/web/auth/login` | Login action |
| POST | `/web/auth/register` | Register action |
| GET | `/web/auth/logout` | Logout action |

## Docker Deployment

### Build Image

```bash
docker build -t llm-service .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e MONGO_URI=mongodb://host:27017 \
  llm-service
```

### Docker Compose Production

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MONGO_URI=mongodb://mongodb:27017
    depends_on:
      mongodb:
        condition: service_healthy

  mongodb:
    image: mongo:7.0
    volumes:
      - mongo-data:/data/db
    healthcheck:
      test: mongosh --eval 'db.adminCommand({ping: 1})'
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mongo-data:
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `MONGO_URI` | Yes | - | MongoDB connection string |
| `MONGO_DB` | No | `langchain` | Database name |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |
| `JWT_SECRET` | No | `supersecret` | JWT signing secret |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model |
| `LANGSMITH_TRACING` | No | `false` | Enable LangSmith |

## Project Structure

```
llm-service-boilerplate/
├── config/
│   └── settings.py
├── shared/
│   ├── models/
│   ├── persistance/
│   └── services/
├── modules/
│   ├── langchain/
│   │   ├── agents/
│   │   ├── services/
│   │   ├── tools/
│   │   └── http_handlers/
│   └── web/
│       ├── services/
│       ├── http_handlers/
│       └── templates/
├── tests/
│   ├── unit/
│   └── integration/
├── .github/
│   └── workflows/
├── main.py
├── Dockerfile
└── docker-compose.yml
```

## License

MIT
