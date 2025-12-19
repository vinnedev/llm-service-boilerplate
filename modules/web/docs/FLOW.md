# Fluxos do Sistema

Este documento contém os diagramas de fluxo do módulo Web usando Mermaid.

## Fluxo Geral de Autenticação

```mermaid
flowchart TD
    A[Usuário acessa /web] --> B{Tem cookie auth_token?}
    B -->|Não| C[Redireciona para /web/login]
    B -->|Sim| D{Token válido?}
    D -->|Não| C
    D -->|Sim| E[Redireciona para /web/chat]
    
    C --> F[Exibe página de login]
    F --> G[Usuário preenche credenciais]
    G --> H[POST /web/auth/login]
    H --> I{Credenciais válidas?}
    I -->|Não| J[Exibe erro]
    J --> F
    I -->|Sim| K[Gera token JWT]
    K --> L[Set-Cookie: auth_token]
    L --> E
```

## Fluxo de Registro

```mermaid
flowchart TD
    A[Usuário acessa /web/register] --> B[Exibe formulário]
    B --> C[Usuário preenche dados]
    C --> D[POST /web/auth/register]
    D --> E{Email já existe?}
    E -->|Sim| F[Exibe erro]
    F --> B
    E -->|Não| G[Hash da senha com bcrypt]
    G --> H[Salva usuário no MongoDB]
    H --> I[Gera token JWT]
    I --> J[Set-Cookie: auth_token]
    J --> K[Redireciona para /web/chat]
```

## Fluxo Principal do Chat

```mermaid
flowchart TD
    A[GET /web/chat] --> B{Usuário autenticado?}
    B -->|Não| C[Redireciona para /login]
    B -->|Sim| D[Carrega sessões do usuário]
    D --> E{session_id na URL?}
    E -->|Não| F[Exibe estado vazio]
    E -->|Sim| G[Carrega sessão]
    G --> H[Busca histórico do checkpointer]
    H --> I[Renderiza chat.html]
    F --> I
    I --> J[Usuário no chat]
```

## Fluxo de Envio de Mensagem

```mermaid
sequenceDiagram
    participant U as Usuário
    participant F as Frontend (chat.html)
    participant B as Backend (chat.py)
    participant A as ConversationAgent
    participant L as LangGraph
    participant O as OpenAI API
    participant M as MongoDB

    U->>F: Digita mensagem
    F->>F: Adiciona mensagem do usuário na UI
    F->>F: Mostra indicador de "digitando"
    F->>B: POST /web/chat/send/{session_id}
    
    B->>B: Valida sessão e usuário
    B->>A: Cria ConversationAgent
    A->>L: stream(message, thread_id)
    
    loop Para cada chunk
        L->>O: Requisição streaming
        O-->>L: Chunk de resposta
        L->>M: Salva checkpoint
        L-->>A: Yield chunk
        A-->>B: Yield chunk
        B-->>F: SSE: data: {"chunk": "..."}
        F->>F: Atualiza mensagem na UI
    end
    
    B-->>F: SSE: data: {"done": true}
    F->>F: Finaliza streaming
    F->>F: Remove indicador de "digitando"
```

## Fluxo de Criação Automática de Sessão

```mermaid
flowchart TD
    A[Usuário digita primeira mensagem] --> B{currentSessionId existe?}
    B -->|Sim| C[Envia mensagem normalmente]
    B -->|Não| D[POST /web/chat/session]
    D --> E[Cria sessão no MongoDB]
    E --> F[Retorna session_id]
    F --> G[Atualiza currentSessionId]
    G --> H[Atualiza URL com pushState]
    H --> I[Adiciona sessão na sidebar]
    I --> J[Esconde estado vazio]
    J --> C
    C --> K[POST /web/chat/send/{session_id}]
```

## Fluxo de Troca de Sessão (Sem Reload)

```mermaid
sequenceDiagram
    participant U as Usuário
    participant F as Frontend
    participant B as Backend

    U->>F: Clica em outra sessão
    F->>F: Verifica se está streaming
    
    alt Está streaming
        F->>F: Ignora clique
    else Não está streaming
        F->>B: GET /web/chat/session/{id}/messages
        B->>B: Valida ownership
        B->>B: Busca mensagens do checkpointer
        B-->>F: JSON {session_id, name, messages}
        
        F->>F: Atualiza currentSessionId
        F->>F: pushState (atualiza URL)
        F->>F: Atualiza header
        F->>F: Atualiza highlight da sidebar
        F->>F: Limpa container de mensagens
        F->>F: Renderiza novas mensagens
        F->>F: Aplica markdown + syntax highlighting
        F->>F: Scroll para o final
    end
```

## Fluxo de Deleção de Sessão

```mermaid
flowchart TD
    A[Usuário clica em deletar] --> B[Confirmação]
    B -->|Cancela| C[Nada acontece]
    B -->|Confirma| D[DELETE /web/chat/session/{id}]
    D --> E[Backend valida ownership]
    E --> F[Deleta checkpoints do LangGraph]
    F --> G[Deleta sessão do MongoDB]
    G --> H{É a sessão atual?}
    H -->|Sim| I[Redireciona para /web/chat]
    H -->|Não| J[Remove elemento da sidebar]
```

## Fluxo de Streaming com Keep-alive

```mermaid
sequenceDiagram
    participant C as Cliente
    participant S as Servidor
    participant Q as Queue
    participant A as Agent Task
    participant K as Keepalive Task

    C->>S: POST /chat/send/{id}
    S->>Q: Cria Queue
    S->>A: Inicia stream_agent()
    S->>K: Inicia keepalive()
    
    par Agent processando
        A->>Q: put({"chunk": "..."})
    and Keepalive loop
        loop A cada 15 segundos
            K->>Q: put(None) se não done
        end
    end
    
    loop Consumir queue
        S->>Q: await get()
        alt item é None
            S-->>C: : keepalive
        else item tem dados
            S-->>C: data: {"chunk": "..."}
        end
    end
    
    A->>Q: put({"done": true})
    S-->>C: data: {"done": true}
    S->>K: Cancela keepalive
```

## Estrutura de Dados

### Sessão

```mermaid
erDiagram
    SESSION {
        string session_id PK
        string thread_id
        string user_id FK
        string name
        datetime created_at
        datetime updated_at
    }
    
    USER {
        string user_id PK
        string email
        string name
        string password_hash
        datetime created_at
        datetime updated_at
    }
    
    CHECKPOINT {
        string thread_id PK
        json checkpoint
        json metadata
        datetime created_at
    }
    
    USER ||--o{ SESSION : has
    SESSION ||--|| CHECKPOINT : linked_to
```

## Estados do Chat

```mermaid
stateDiagram-v2
    [*] --> SemSessao: Abre /web/chat
    
    SemSessao --> Digitando: Usuário digita
    Digitando --> CriandoSessao: Enter sem sessão
    CriandoSessao --> Streaming: Sessão criada
    
    SemSessao --> CarregandoMensagens: Clica em sessão
    CarregandoMensagens --> Idle: Mensagens carregadas
    
    Idle --> Digitando: Usuário digita
    Digitando --> Streaming: Enter com sessão
    
    Streaming --> Idle: Resposta completa
    Streaming --> Erro: Falha
    Erro --> Idle: Retry
    
    Idle --> CarregandoMensagens: Troca sessão
    Idle --> SemSessao: Deleta sessão atual
```

## Componentes do Frontend

```mermaid
graph TB
    subgraph chat.html
        A[Sidebar] --> A1[Lista de Sessões]
        A1 --> A2[Botão Nova Conversa]
        A1 --> A3[Sessão Item]
        A3 --> A3a[Renomear]
        A3 --> A3b[Deletar]
        
        B[Main Area] --> B1[Header]
        B --> B2[Messages Container]
        B --> B3[Input Area]
        
        B2 --> B2a[User Message]
        B2 --> B2b[Assistant Message]
        B2b --> B2c[Markdown Rendered]
        B2b --> B2d[Code Highlighted]
        
        B3 --> B3a[Text Input]
        B3 --> B3b[Send Button]
    end
```

## Ciclo de Vida da Requisição

```mermaid
flowchart LR
    subgraph Request
        A[HTTP Request] --> B[FastAPI Router]
        B --> C[Middleware]
        C --> D[Dependencies]
        D --> E[Handler]
    end
    
    subgraph Processing
        E --> F[Service]
        F --> G[MongoDB]
    end
    
    subgraph Response
        G --> H[Model]
        H --> I[JSON/HTML]
        I --> J[HTTP Response]
    end
```
