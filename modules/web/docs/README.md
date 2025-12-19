# Documentação do Módulo Web

## Visão Geral

O módulo Web é responsável pela interface de usuário do sistema de chat com LLM. Utiliza uma arquitetura moderna com:

- **FastAPI** - Framework web assíncrono
- **Jinja2** - Templates server-side
- **HTMX** - Interatividade sem JavaScript complexo
- **Tailwind CSS** - Estilização utility-first
- **SSE (Server-Sent Events)** - Streaming de respostas em tempo real

## Estrutura de Arquivos

```
modules/web/
├── docs/
│   ├── README.md              # Esta documentação
│   ├── ARCHITECTURE.md        # Arquitetura detalhada
│   └── FLOW.md                # Diagramas de fluxo
├── http_handlers/
│   ├── __init__.py
│   ├── auth.py                # Endpoints de autenticação
│   ├── chat.py                # Endpoints do chat (API JSON)
│   └── pages.py               # Páginas HTML
├── services/
│   ├── __init__.py
│   └── auth_service.py        # Lógica de autenticação
└── templates/
    ├── base.html              # Template base
    ├── login.html             # Página de login
    ├── register.html          # Página de registro
    └── chat.html              # Interface do chat
```

## Endpoints

### Páginas (HTML)

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/web/` | Home - redireciona baseado em auth | Não |
| GET | `/web/login` | Página de login | Não |
| GET | `/web/register` | Página de registro | Não |
| GET | `/web/chat` | Interface do chat | Sim |

### Autenticação (JSON)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/web/auth/register` | Criar conta |
| POST | `/web/auth/login` | Fazer login |
| GET | `/web/auth/logout` | Fazer logout |

### Chat (JSON API)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/web/chat/session` | Criar nova sessão |
| DELETE | `/web/chat/session/{id}` | Deletar sessão |
| PATCH | `/web/chat/session/{id}` | Renomear sessão |
| GET | `/web/chat/session/{id}/messages` | Buscar mensagens |
| POST | `/web/chat/send/{id}` | Enviar mensagem (SSE) |

## Autenticação

O sistema usa autenticação baseada em cookies:

1. **Registro**: Cria usuário com senha hasheada (bcrypt)
2. **Login**: Valida credenciais e gera token JWT
3. **Cookie**: Token armazenado em `auth_token` (HttpOnly)
4. **Validação**: Cada request protegido valida o token

## Fluxo do Chat

Ver [FLOW.md](./FLOW.md) para diagramas detalhados.

### Resumo:

1. Usuário acessa `/web/chat`
2. Se não autenticado, redireciona para login
3. Carrega sessões do usuário do MongoDB
4. Ao enviar mensagem:
   - Frontend faz POST para `/web/chat/send/{session_id}`
   - Backend processa via LangGraph
   - Resposta é streamada via SSE
   - Frontend renderiza chunks em tempo real

## Templates

### base.html
Template base com:
- Tailwind CSS (CDN)
- HTMX
- Marked.js (Markdown)
- Highlight.js (Syntax highlighting)
- Estilos globais

### chat.html
Interface principal com:
- Sidebar de sessões
- Área de mensagens
- Input com streaming
- Suporte a markdown nas respostas
- Troca de sessões sem reload

## Tecnologias Frontend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Tailwind CSS | 3.x (CDN) | Estilização |
| HTMX | 1.9.10 | Interatividade |
| Marked.js | latest | Renderização Markdown |
| Highlight.js | 11.9.0 | Syntax highlighting |

## Configuração

Variáveis de ambiente relevantes (via `config/settings.py`):

```env
SECRET_KEY=sua-chave-secreta
MONGO_URI=mongodb://localhost:27017
MONGO_DB=nome-database
```

## Dependências Internas

O módulo Web depende de:

- `shared.models.users_model` - Modelo de usuário
- `shared.models.sessions_model` - Modelo de sessão
- `shared.services.logger` - Serviço de logging
- `shared.persistance.mongo_db` - Pool de conexões MongoDB
- `modules.langchain.services.session_service` - CRUD de sessões
- `modules.langchain.services.checkpointer` - Factory do checkpointer
- `modules.langchain.agents.conversation_agent` - Agente de conversação
