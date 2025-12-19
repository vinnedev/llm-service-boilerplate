# Arquitetura do Módulo Web

## Visão Geral da Arquitetura

O módulo Web segue o padrão **Modular Monolith** com separação clara de responsabilidades:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              MÓDULO WEB                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │   HTTP Handlers  │  │    Services      │  │    Templates     │      │
│  │                  │  │                  │  │                  │      │
│  │  • auth.py       │  │  • auth_service  │  │  • base.html     │      │
│  │  • chat.py       │  │                  │  │  • login.html    │      │
│  │  • pages.py      │  │                  │  │  • register.html │      │
│  │                  │  │                  │  │  • chat.html     │      │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────────────┘      │
│           │                     │                                        │
│           └─────────────────────┴────────────────────────────────────┐  │
│                                                                       │  │
│  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │                    Dependency Injection                         │  │  │
│  │                                                                 │  │  │
│  │  get_auth_service() → AuthService                              │  │  │
│  │  get_session_service() → SessionService                        │  │  │
│  │  get_checkpointer_factory() → CheckpointerFactory              │  │  │
│  │  get_current_user() → Optional[UsersModel]                     │  │  │
│  │  require_user() → UsersModel (raises 401)                      │  │  │
│  └────────────────────────────────────────────────────────────────┘  │  │
│                                                                       │  │
└───────────────────────────────────────────────────────────────────────┴──┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           MÓDULO LANGCHAIN                               │
├─────────────────────────────────────────────────────────────────────────┤
│  • SessionService        - CRUD de sessões                              │
│  • CheckpointerFactory   - Cria instâncias MongoDBSaver                 │
│  • ConversationAgent     - Wrapper do agente LangGraph                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              SHARED                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  • UsersModel            - Modelo Pydantic de usuário                   │
│  • SessionsModel         - Modelo Pydantic de sessão                    │
│  • mongo_pool            - Pool de conexões MongoDB                     │
│  • logger                - Serviço de logging                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Padrões Utilizados

### 1. Dependency Injection (FastAPI Depends)

```python
def get_auth_service() -> AuthService:
    return AuthService()

@router.post("/login")
async def login(
    auth_service: AuthService = Depends(get_auth_service)
):
    ...
```

### 2. Repository Pattern

Os services encapsulam o acesso a dados:

```python
class AuthService:
    def create_user(self, data: UserCreate) -> UsersModel
    def authenticate(self, email: str, password: str) -> Optional[UsersModel]
    def get_user_by_token(self, token: str) -> Optional[UsersModel]
```

### 3. Factory Pattern

```python
class CheckpointerFactory:
    def __init__(self, client: MongoClient):
        self._client = client
    
    def create(self) -> MongoDBSaver:
        return MongoDBSaver(client=self._client, ...)
```

## Camadas da Aplicação

```
┌─────────────────────────────────────────────────┐
│                 HTTP Layer                       │
│  (FastAPI Routers, Request/Response handling)    │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                Service Layer                     │
│  (Business Logic, Validation, Auth)              │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│               Data Access Layer                  │
│  (MongoDB, Pydantic Models)                      │
└─────────────────────────────────────────────────┘
```

## Fluxo de Requisição

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Router    │  ← Seleciona handler baseado na rota
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Middleware  │  ← CORS, Logging, etc.
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Dependencies │  ← Injeção de dependências (auth, services)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Handler    │  ← Lógica do endpoint
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Service    │  ← Regras de negócio
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  MongoDB    │  ← Persistência
└─────────────┘
```

## Autenticação

### Fluxo de Login

```
┌────────┐     POST /auth/login      ┌────────────┐
│ Client │ ─────────────────────────►│ AuthService│
└────────┘    {email, password}      └──────┬─────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │ Verify Hash  │
                                     │ (bcrypt)     │
                                     └──────┬───────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │ Generate JWT │
                                     │ Token        │
                                     └──────┬───────┘
                                            │
┌────────┐     Set-Cookie: auth_token       │
│ Client │ ◄────────────────────────────────┘
└────────┘
```

### Validação de Token

```python
async def require_user(request: Request, auth_service: AuthService):
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401)
    
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401)
    
    return user
```

## SSE Streaming

O chat usa Server-Sent Events para streaming:

```
Client                              Server
  │                                    │
  │  POST /chat/send/{session_id}     │
  │ ──────────────────────────────────►│
  │                                    │
  │  HTTP 200 OK                       │
  │  Content-Type: text/event-stream   │
  │ ◄──────────────────────────────────│
  │                                    │
  │  data: {"chunk": "Olá"}            │
  │ ◄──────────────────────────────────│
  │                                    │
  │  data: {"chunk": ", como"}         │
  │ ◄──────────────────────────────────│
  │                                    │
  │  data: {"chunk": " posso"}         │
  │ ◄──────────────────────────────────│
  │                                    │
  │  : keepalive                       │  (a cada 15s)
  │ ◄──────────────────────────────────│
  │                                    │
  │  data: {"done": true}              │
  │ ◄──────────────────────────────────│
  │                                    │
```

## Segurança

### Headers de Segurança

- `HttpOnly` cookies para tokens
- `SameSite=Lax` para CSRF básico
- `Cache-Control: no-cache` para SSE

### Validações

- Ownership check em todas operações de sessão
- Senha hasheada com bcrypt
- Token JWT com expiração
- Sanitização de input no frontend

## Performance

### Otimizações Implementadas

1. **Lazy Loading**: Serviços criados sob demanda
2. **Connection Pool**: MongoDB usa pool de conexões
3. **SSE Keep-alive**: Previne timeout em conexões longas
4. **Dynamic Loading**: Troca de sessões sem reload
5. **Streaming**: Respostas do LLM em tempo real
