---
title: Child Safe AI Learning Assistant Requirements
document_type: Product and technical requirements
version: "1.0"
prepared: 2026-09-13
---

# Child Safe AI Learning Assistant Requirements

> **Purpose:** This document defines the product, safety, data, architecture, deployment and acceptance requirements for a private AI learning assistant used by children and administered by an adult. It is written so an agentic development tool can convert the requirements into epics, stories, migrations, APIs, tests and deployment tasks.

**Proposed technology**

React with TypeScript and Vite \| FastAPI with Python \| Supabase \| Railway \| Vercel \| OpenAI API

## Executive Summary

The product will provide children with a simple, age-aware chat experience for asking educational questions. The application will store conversations in Supabase, classify questions by topic and subtopic, support keyword and semantic search across prior interactions, and gradually build a reviewed knowledge base for retrieval augmented generation. An adult administrator will manage prompts, taxonomy, knowledge approval, users, safety events and operational configuration through a protected administration interface.

The recommended architecture uses a React TypeScript application on Vercel, a FastAPI service on Railway and Supabase for authentication, Postgres data, row-level security and pgvector. The browser may use the Supabase publishable key for authentication, but all model calls, administrative operations, secret-key use and prompt assembly must occur on the server.

> **Primary design decision:** Raw model answers must never enter the RAG knowledge base automatically. Questions may be classified immediately for analytics, but an answer becomes retrievable knowledge only after review or an explicit approval rule. This prevents an inaccurate model response from being repeated as trusted content.

## Product Goals

- Give a child a focused and easy way to ask educational questions and revisit earlier learning.

- Apply age-aware safety controls before and after every model call.

- Organize questions by topic and subtopic so learning interests and recurring needs become visible over time.

- Support search across the child’s own history using keywords and semantic similarity.

- Create a reviewed knowledge corpus that can improve future answers without treating unverified model output as fact.

- Allow an administrator to version prompts, review content, manage taxonomy and inspect safety and usage information.

- Keep deployment simple enough for a private family application while preserving a path to multiple children and wider use.

### Success Measures

| **Measure**                | **Initial target**                                                                | **How measured**                                     |
|----------------------------|-----------------------------------------------------------------------------------|------------------------------------------------------|
| Successful answer delivery | At least 98 percent of valid requests                                             | Completed chat requests divided by accepted requests |
| Unsafe output exposure     | Zero in the approved safety test suite                                            | Pre-release and regression red-team tests            |
| History search usefulness  | Relevant result in the first five results for at least 85 percent of test queries | Curated search evaluation set                        |
| Classification quality     | At least 90 percent top-level topic accuracy                                      | Administrator-reviewed sample                        |
| RAG grounding              | Every retrieved item is approved and traceable                                    | Retrieval audit log                                  |
| Prompt traceability        | Every model run records prompt version identifiers                                | LLM run records                                      |

## Scope

### Minimum Viable Product

- Private deployment for one family with support for multiple child profiles.

- Text-based chat with a non-streamed response until output moderation completes.

- Conversation list, prior-question list and search across the signed-in child’s history.

- Automatic topic and subtopic classification with confidence and model-version recording.

- Administrator login, prompt version management, taxonomy management and knowledge review.

- Supabase Auth, Postgres, full-text search and pgvector-based semantic search.

- OpenAI chat, moderation and embedding APIs behind the FastAPI service.

- Railway backend deployment and Vercel frontend deployment.

### Deferred Features

| **Feature**                      | **Suggested phase** | **Reason for deferral**                                                   |
|----------------------------------|---------------------|---------------------------------------------------------------------------|
| Voice input and output           | Phase 2             | Requires separate safety, privacy and transcription handling              |
| Images and file uploads          | Phase 2             | Requires media moderation, storage policies and retention rules           |
| Unrestricted web search          | Phase 3             | External content creates additional child-safety and source-quality risk  |
| Native mobile application        | Phase 3             | Responsive web is sufficient for the initial family use case              |
| Child-to-child sharing           | Out of scope        | Introduces social and moderation risks not required for the learning goal |
| Direct key entry in the admin UI | Deferred            | Secrets should remain in managed deployment environments                  |

## Assumptions and Decisions

| **Area**             | **First-draft assumption**                                              | **Later decision**                                                                  |
|----------------------|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Audience             | Private family use rather than a public product                         | Reassess legal, consent and support requirements before wider release               |
| Child authentication | Each child has an individual account or an adult-selected child profile | Choose email login, magic link or parent-managed PIN during implementation planning |
| Administrator URL    | One React codebase with protected /admin routes                         | A separate admin subdomain can be added without changing the backend model          |
| Model provider       | OpenAI through a provider abstraction                                   | Additional providers may be introduced behind the same interface                    |
| Search               | Hybrid keyword and semantic search                                      | Tune ranking weights using real query evaluations                                   |
| RAG corpus           | Only reviewed or explicitly approved items                              | Define whether some trusted imported sources may be auto-approved                   |
| Retention            | Configurable retention with conservative defaults                       | Set exact periods after confirming child age and applicable law                     |

## Users and Roles

| **Role**      | **Capabilities**                                                                                                | **Restrictions**                                                                       |
|---------------|-----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| Child         | Ask questions, view own conversations, search own history, rename or archive own conversations where allowed    | Cannot access other profiles, prompts, raw safety logs, secrets or administrative APIs |
| Guardian      | Manage linked child profiles, review permitted summaries, manage retention and receive configured safety alerts | Access must follow the selected child-privacy model                                    |
| Administrator | Manage prompts, taxonomy, knowledge approval, users, safety events, usage and system configuration              | Role must be server-verified and cannot rely on a hidden URL                           |
| System worker | Classify, embed, summarize and run retention jobs                                                               | No interactive login; least-privilege service access                                   |

## Child Experience Requirements

### Chat Interface

| **ID**   | **Requirement**                                                                                         | **Priority** |
|----------|---------------------------------------------------------------------------------------------------------|--------------|
| CHAT 001 | The child can start a new conversation from a prominent text box.                                       | P0           |
| CHAT 002 | The interface shows the child’s message, a processing state and the approved assistant response.        | P0           |
| CHAT 003 | The application does not display generated text until mandatory output safety checks complete.          | P0           |
| CHAT 004 | The child can continue a conversation and the backend supplies the required recent context and summary. | P0           |
| CHAT 005 | The response may show sources or retrieved prior items when RAG contributes to the answer.              | P1           |
| CHAT 006 | The child can provide simple feedback such as helpful, not helpful or report a problem.                 | P1           |
| CHAT 007 | Error messages use child-friendly language and never reveal provider errors, prompts or keys.           | P0           |
| CHAT 008 | The UI prevents accidental duplicate submission and enforces configured input and output limits.        | P0           |

### History and Search

| **ID**   | **Requirement**                                                                                           | **Priority** |
|----------|-----------------------------------------------------------------------------------------------------------|--------------|
| HIST 001 | A side panel lists recent conversations or recent questions, ordered by last activity.                    | P0           |
| HIST 002 | Selecting an item opens the corresponding conversation and scrolls to the selected question.              | P0           |
| HIST 003 | A history search field finds prior questions and answers within the signed-in child’s permitted data.     | P0           |
| HIST 004 | Search combines keyword matches with semantic similarity and returns a short highlighted excerpt.         | P1           |
| HIST 005 | Results can be filtered by topic, subtopic and date range.                                                | P1           |
| HIST 006 | The child can start a follow-up conversation from an earlier answer without altering the original record. | P1           |
| HIST 007 | No child can retrieve another child’s content, including through search or guessed identifiers.           | P0           |

### Child Interface Layout

| **Region**   | **Desktop**                                               | **Mobile**                                       |
|--------------|-----------------------------------------------------------|--------------------------------------------------|
| Top bar      | Product name, new chat, child profile and sign out        | Compact title, new chat and profile menu         |
| History      | Persistent or collapsible left side panel with search     | Slide-over drawer                                |
| Conversation | Centered readable column with question and response cards | Full-width stacked cards                         |
| Composer     | Sticky text box with submit control                       | Sticky multiline input above the safe-area inset |
| Status       | Short processing, blocked, retry or escalation messages   | Same content with touch-friendly actions         |

## Administration Requirements

### Authentication and Access

| **ID**  | **Requirement**                                                                                                    | **Priority** |
|---------|--------------------------------------------------------------------------------------------------------------------|--------------|
| ADM 001 | The admin area is available only after Supabase authentication and server-side role verification.                  | P0           |
| ADM 002 | Administrative authorization uses trusted app metadata or a protected role table and never user-editable metadata. | P0           |
| ADM 003 | The /admin route and every /v1/admin API reject non-admin users independently.                                     | P0           |
| ADM 004 | MFA is supported for administrator accounts before any public or multi-family release.                             | P1           |
| ADM 005 | Administrative actions that alter prompts, approvals, taxonomy or users create audit records.                      | P0           |

### Prompt Management

| **ID**  | **Requirement**                                                                                                                                                   | **Priority** |
|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| PRM 001 | The administrator can create named prompt definitions for base behavior, age-band behavior, classification, response generation, summarization and safety review. | P0           |
| PRM 002 | Editing a prompt creates an immutable version instead of overwriting a published version.                                                                         | P0           |
| PRM 003 | Each version has draft, active, retired or rolled-back status with author and timestamps.                                                                         | P0           |
| PRM 004 | The administrator can preview the assembled prompt for a synthetic test request with secrets and child identifiers redacted.                                      | P0           |
| PRM 005 | Publishing a prompt requires test execution against a stored evaluation set and an explicit confirmation.                                                         | P1           |
| PRM 006 | Every model run records the identifiers of all prompt versions used.                                                                                              | P0           |
| PRM 007 | Stable prompt content is placed before dynamic content to improve prompt-cache reuse.                                                                             | P1           |

### Content and Taxonomy Management

| **ID**  | **Requirement**                                                                                                                   | **Priority** |
|---------|-----------------------------------------------------------------------------------------------------------------------------------|--------------|
| CNT 001 | The administrator can create, rename, merge, deactivate and hierarchically arrange topics and subtopics.                          | P0           |
| CNT 002 | The administrator can review low-confidence or disputed classifications and correct them without modifying the original question. | P0           |
| CNT 003 | The administrator can review candidate knowledge items and mark them approved, rejected, revised or archived.                     | P0           |
| CNT 004 | Approved knowledge retains provenance to the original conversation or imported source and the approving administrator.            | P0           |
| CNT 005 | Editing approved knowledge creates a new version and queues regeneration of its embedding.                                        | P0           |
| CNT 006 | The administrator can inspect safety events with access limited to what is necessary for review.                                  | P1           |

## AI Request Processing

### Required Processing Sequence

1.  Authenticate the caller and load the authorized child profile.

2.  Validate request size, rate limits and conversation ownership.

3.  Run input moderation and application-specific risk classification.

4.  Classify the educational topic and subtopic with confidence scores.

5.  Retrieve only approved knowledge that matches permissions, age band and topic filters.

6.  Assemble the active base prompt, age-band prompt, relevant skill instructions, conversation context and retrieved evidence.

7.  Call the configured model and record provider usage metadata.

8.  Run output moderation and the application’s age-appropriateness check.

9.  Return an approved response, a safe transformed response or an escalation response.

10. Persist the message pair, classifications, run metadata and safety outcome; queue eligible embedding and summarization work.

### Prompt Assembly Order

1. Stable base safety and role instructions
2. Stable age band instructions
3. Relevant tool and skill definitions
4. Dynamic child profile fields
5. Conversation summary and recent turns
6. Approved retrieved knowledge
7. Current child message

The stable prefix must be kept byte-for-byte consistent where practical. Dynamic values such as the child’s current question, time, retrieved records and conversation summary must come after the cache breakpoint.

### Safety Outcomes

| **Outcome** | **System behavior**                                                                   | **Display behavior**                                                   |
|-------------|---------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| Allow       | Generate and validate the normal answer                                               | Show the answer                                                        |
| Transform   | Replace unsafe detail with an age-appropriate explanation                             | Show the transformed answer                                            |
| Refuse      | Decline procedural or clearly inappropriate help and offer a safe alternative         | Show a brief refusal and redirection                                   |
| Support     | Use supportive handling for sensitive but legitimate questions                        | Provide factual guidance and suggest a trusted adult where appropriate |
| Escalate    | Create a restricted safety event and follow the configured guardian process           | Show calm immediate-safety guidance without exposing internal actions  |
| Fail closed | If a mandatory safety dependency fails, do not expose the unreviewed generated output | Show a retry message                                                   |

### Model and Provider Requirements

- Model, moderation model, embedding model, response length and reasoning settings are server configuration values.

- Provider-specific code is isolated behind ChatProvider, ModerationProvider and EmbeddingProvider interfaces.

- Every run records provider, model, model configuration, prompt versions, latency and token usage.

- Prompt caching is enabled where supported, but the application never depends on a cache hit for safety instructions.

- A provider outage or moderation failure must not result in unsafe output being displayed.

- The browser never calls the model provider directly.

## Classification and Knowledge Requirements

### Taxonomy

The taxonomy is hierarchical. A question may have one primary topic, one primary subtopic and optional additional labels. Initial top-level topics may include History, Geography, Science, Mathematics, Language, Technology, Arts and General Knowledge. Administrators may change this list without a database migration.

| **Field**        | **Requirement**                                              |
|------------------|--------------------------------------------------------------|
| Primary topic    | Required when classification succeeds                        |
| Primary subtopic | Optional when the taxonomy does not contain a suitable child |
| Confidence       | Numeric score with a configurable review threshold           |
| Classifier       | Provider, model, prompt version and taxonomy version         |
| Source           | Automatic, administrator corrected or rule based             |
| Review state     | Unreviewed, confirmed or corrected                           |

### RAG Corpus Policy

> **Approval boundary:** Conversation storage, analytics and RAG are different concerns. The system may store a response for the child to revisit, but it must not use that response as trusted retrieval evidence until an administrator approves or revises it.

| **Content state**              | **Searchable in child history**              | **Retrievable as RAG evidence** |
|--------------------------------|----------------------------------------------|---------------------------------|
| Raw question                   | Yes for its owner                            | No                              |
| Raw model response             | Yes for its owner if it passed safety checks | No                              |
| Candidate knowledge            | Admin only                                   | No                              |
| Approved knowledge             | According to audience rules                  | Yes                             |
| Rejected or archived knowledge | Admin only                                   | No                              |
| Trusted imported source        | According to audience rules                  | Yes after source approval       |

### Search Design

- History search filters by the signed-in child before ranking results.

- Knowledge retrieval filters by approved status, audience age band, locale and optional topic before ranking.

- Hybrid search combines Postgres full-text search with pgvector semantic similarity.

- The same embedding model and dimensionality are used for stored content and query embeddings.

- Every embedding stores its model and version so a model change can trigger controlled re-embedding.

- Vector indexes are added when evaluation or row volume justifies them; HNSW is the expected initial index for a read-heavy corpus.

- Search quality is measured with a fixed evaluation set before ranking weights or similarity thresholds change.

## System Architecture

| **Component**           | **Responsibility**                                                                           | **Hosting**                           |
|-------------------------|----------------------------------------------------------------------------------------------|---------------------------------------|
| Child React application | Chat, history, search and child session experience                                           | Vercel                                |
| Admin React application | Prompt, taxonomy, review, users, safety and operations                                       | Vercel in the same codebase initially |
| FastAPI service         | Authorization, prompt assembly, safety orchestration, provider calls and administrative APIs | Railway                               |
| Background worker       | Embedding, classification retry, summarization and retention jobs                            | Railway worker or scheduled service   |
| Supabase Auth           | User identity and sessions                                                                   | Supabase                              |
| Supabase Postgres       | Application data, audit records, full-text search and vector storage                         | Supabase                              |
| OpenAI APIs             | Chat generation, moderation and embeddings                                                   | OpenAI                                |

### Request Flow

1. Browser
2. Supabase Auth for sign in
3. FastAPI with Supabase access token
4. Input policy and moderation
5. Topic classification and approved knowledge retrieval
6. OpenAI generation
7. Output policy and moderation
8. Supabase persistence
9. Safe response to browser

The frontend may use the Supabase publishable key for authentication. It must send the user access token to FastAPI, which verifies identity and authorization before reading or writing protected records. A hidden route or client-side route guard is never the sole protection for admin capabilities.

## Data Model

The following logical model is sufficient for the first implementation. Exact column names may change during detailed design, but ownership, versioning and approval boundaries are required.

| **Table**               | **Purpose**                                          | **Key fields**                                                                                            |
|-------------------------|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| profiles                | Application identity linked to Supabase Auth         | id, display_name, status, created_at                                                                      |
| user_roles              | Trusted application roles                            | user_id, role, granted_by, granted_at                                                                     |
| child_profiles          | Child-specific settings and guardian relationship    | id, auth_user_id, guardian_user_id, age_band, grade_level, locale, settings                               |
| conversations           | Conversation header and rolling summary              | id, child_profile_id, title, summary, status, last_message_at                                             |
| messages                | Immutable user and assistant turns                   | id, conversation_id, role, content, safety_state, created_at                                              |
| topics                  | Hierarchical taxonomy                                | id, parent_id, name, slug, active, taxonomy_version                                                       |
| message_classifications | Topic assignments and confidence                     | message_id, topic_id, confidence, source, model, prompt_version_id                                        |
| prompt_definitions      | Stable prompt purpose                                | id, key, type, description                                                                                |
| prompt_versions         | Immutable prompt text and lifecycle                  | id, prompt_definition_id, version, content, status, created_by                                            |
| prompt_assignments      | Maps active prompts to age band or workflow          | id, workflow, age_band, prompt_version_id, active_from                                                    |
| knowledge_items         | Reviewed retrieval corpus                            | id, question, answer, approval_state, audience, source_message_id, approved_by                            |
| knowledge_embeddings    | Versioned vectors and search text                    | knowledge_item_id, embedding, embedding_model, dimensions, content_hash                                   |
| llm_runs                | Traceability, cost and diagnostics                   | id, request_message_id, response_message_id, provider, model, prompt_versions, tokens, latency_ms, status |
| safety_events           | Restricted risk and moderation events                | id, child_profile_id, message_id, category, severity, action, review_state                                |
| feedback                | Child or guardian response feedback                  | id, message_id, user_id, rating, reason, created_at                                                       |
| audit_logs              | Administrator and system changes                     | id, actor_id, action, entity_type, entity_id, before_hash, after_hash, created_at                         |
| background_jobs         | Retryable classification, embedding and summary work | id, type, entity_id, state, attempts, next_attempt_at, error_code                                         |

### Database Rules and Indexes

- Enable row-level security on every table in an exposed schema.

- Index all ownership and policy columns, including child_profile_id, conversation_id, user_id and guardian_user_id.

- Use foreign keys for ownership and provenance relationships and define intentional delete behavior.

- Use created_at and updated_at timestamps in UTC and avoid using timestamps as primary keys.

- Add a GIN index for generated full-text search columns used by history or knowledge search.

- Add a vector index using the same distance operator as the retrieval query.

- Keep vector filtering inside the retrieval SQL function so topic and audience constraints apply before final ranking.

- Use migrations for every schema change and seed only non-sensitive taxonomy and evaluation fixtures.

### Row Level Security Requirements

| **Data**                   | **Child access**                                   | **Guardian access**                         | **Admin access**                        |
|----------------------------|----------------------------------------------------|---------------------------------------------|-----------------------------------------|
| Child profile              | Own profile only                                   | Linked profiles according to policy         | All for support and configuration       |
| Conversations and messages | Own records only                                   | Only according to configured privacy policy | Restricted operational access           |
| Prompts and assignments    | No direct access                                   | No direct access                            | Read and manage                         |
| Knowledge items            | Approved audience-compatible items through backend | Same or broader according to policy         | Review and manage                       |
| Safety events              | No raw event access                                | Configured alerts or summaries              | Restricted review access                |
| Audit logs                 | None                                               | None                                        | Read only for authorized administrators |

## API Requirements

### Child APIs

| **Method and path**             | **Purpose**                                   | **Notes**                        |
|---------------------------------|-----------------------------------------------|----------------------------------|
| POST /v1/chat/messages          | Submit a question and receive a safe response | Idempotency key required         |
| GET /v1/conversations           | List authorized conversations                 | Cursor pagination                |
| POST /v1/conversations          | Create a conversation                         | May be implicit on first message |
| GET /v1/conversations/{id}      | Load messages                                 | Ownership checked server side    |
| PATCH /v1/conversations/{id}    | Rename or archive                             | Allowed fields only              |
| GET /v1/history/search          | Hybrid search across authorized history       | Query, filters and cursor        |
| POST /v1/messages/{id}/feedback | Record feedback or report                     | Rate limited                     |

### Admin APIs

| **Method and path**                         | **Purpose**                                    |
|---------------------------------------------|------------------------------------------------|
| GET and POST /v1/admin/prompts              | List and create prompt definitions             |
| POST /v1/admin/prompts/{id}/versions        | Create an immutable prompt version             |
| POST /v1/admin/prompt-versions/{id}/publish | Test and activate a version                    |
| GET and POST /v1/admin/topics               | List and maintain taxonomy                     |
| GET /v1/admin/knowledge/candidates          | List review queue                              |
| POST /v1/admin/knowledge/{id}/decision      | Approve, revise, reject or archive             |
| GET /v1/admin/safety-events                 | Review restricted safety events                |
| GET /v1/admin/usage                         | Review volume, latency, errors and token usage |
| GET /v1/admin/audit-logs                    | Review administrative changes                  |

### API Standards

- Use versioned JSON APIs under /v1 with generated OpenAPI documentation disabled or access-controlled in production.

- Validate all payloads with typed request and response schemas.

- Return stable error codes separately from child-facing messages.

- Require authentication for every application endpoint except health checks.

- Apply per-user and per-IP rate limits and a maximum request size.

- Use cursor pagination for conversations, messages, review queues and audit logs.

- Propagate a request identifier through frontend, backend, provider calls and logs.

- Do not return moderation scores, prompt text, stack traces or secrets to child clients.

## Security and Privacy

> **Security boundary:** The admin URL is a navigation choice, not an access-control mechanism. Supabase authentication, row-level security and server-side authorization must independently prevent unauthorized access.

| **ID**  | **Requirement**                                                                                                             | **Priority** |
|---------|-----------------------------------------------------------------------------------------------------------------------------|--------------|
| SEC 001 | Use the Supabase publishable key only in the frontend and pair it with correctly tested RLS policies.                       | P0           |
| SEC 002 | Keep the Supabase secret or service-role key, database credentials and OpenAI key only in server-side secret environments.  | P0           |
| SEC 003 | Never place authorization roles in user-editable metadata.                                                                  | P0           |
| SEC 004 | Do not store API keys in ordinary application tables or browser storage.                                                    | P0           |
| SEC 005 | Encrypt transport with HTTPS and reject non-TLS production traffic.                                                         | P0           |
| SEC 006 | Redact personal data and message content from logs unless explicitly required for a restricted investigation.               | P0           |
| SEC 007 | Support deletion of a child profile and its data according to a documented retention and deletion process.                  | P0           |
| SEC 008 | Record and alert on repeated authorization failures, prompt-injection attempts and abnormal request volume.                 | P1           |
| SEC 009 | Run automated RLS tests for child, guardian, admin, anonymous and service contexts.                                         | P0           |
| SEC 010 | Complete legal and privacy review before use by children under the applicable digital-consent age or before public release. | P0           |

### Privacy Controls

- Define separate retention periods for raw messages, summaries, classifications, safety events, provider traces and audit logs.

- Allow the administrator to disable long-term conversation storage while retaining aggregate usage metrics.

- Do not collect real name, exact birth date, location, school or contact data unless a confirmed requirement justifies it.

- Use age bands rather than birth dates where possible.

- Make guardian visibility clear to the child in age-appropriate language.

- Treat zero-data-retention provider configuration as a separate contractual and technical control; do not equate it with a single API request flag.

## Deployment and Configuration

### Vercel Frontend Variables

| **Variable**                  | **Visibility** | **Purpose**                                       |
|-------------------------------|----------------|---------------------------------------------------|
| VITE_API_BASE_URL             | Public         | Railway FastAPI base URL                          |
| VITE_SUPABASE_URL             | Public         | Supabase project URL for authentication           |
| VITE_SUPABASE_PUBLISHABLE_KEY | Public         | Supabase browser key used with RLS                |
| VITE_APP_ENV                  | Public         | Environment label for UI behavior and diagnostics |

> **Forbidden frontend variables:** Do not create `VITE_OPENAI_API_KEY`, `VITE_SUPABASE_SECRET_KEY`, `VITE_SERVICE_ROLE_KEY`, `VITE_DATABASE_URL` or any equivalent browser-visible secret.

### Railway Backend Variables

| **Variable**             | **Required** | **Purpose**                                          |
|--------------------------|--------------|------------------------------------------------------|
| APP_ENV                  | Yes          | Runtime environment                                  |
| ALLOWED_ORIGINS          | Yes          | Exact Vercel production and preview origins          |
| SUPABASE_URL             | Yes          | Auth and platform endpoint                           |
| SUPABASE_PUBLISHABLE_KEY | Yes          | Non-privileged server operations where appropriate   |
| SUPABASE_SECRET_KEY      | Yes          | Privileged server-only operations                    |
| DATABASE_URL             | Yes          | Pooled application database connection               |
| DATABASE_DIRECT_URL      | Recommended  | Direct connection for migrations                     |
| OPENAI_API_KEY           | Yes          | Server-side model access                             |
| OPENAI_CHAT_MODEL        | Yes          | Configured chat model                                |
| OPENAI_MODERATION_MODEL  | Yes          | Configured moderation model                          |
| OPENAI_EMBEDDING_MODEL   | Yes          | Configured embedding model                           |
| EMBEDDING_DIMENSIONS     | Yes          | Must match the Postgres vector column                |
| PROMPT_CACHE_MODE        | Optional     | Supported prompt-cache behavior                      |
| LOG_LEVEL                | Yes          | Structured logging level                             |
| ERROR_REPORTING_DSN      | Optional     | Server error reporting without child message content |

### Secret Management

The first release must manage secrets in Railway and Vercel deployment settings, not through the application’s admin interface. The admin interface may show whether a provider is configured and the last successful health check, but it must not display or return secret values. A later key-management feature requires a dedicated secrets manager, encryption, masked display, rotation and separate authorization before it enters scope.

### Environment Strategy

| **Environment** | **Purpose**                                          | **Data**                          |
|-----------------|------------------------------------------------------|-----------------------------------|
| Local           | Development and automated tests                      | Synthetic child data only         |
| Staging         | Prompt evaluation, migrations and end-to-end testing | Synthetic or anonymized fixtures  |
| Production      | Family use                                           | Real data with approved retention |

## Nonfunctional Requirements

| **Area**        | **Requirement**                                                                                                                        |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Performance     | Chat submission should acknowledge within one second and normally complete within fifteen seconds, excluding declared provider delays. |
| Availability    | The UI remains usable for history browsing when the model provider is unavailable, where cached application data permits.              |
| Accessibility   | Meet WCAG 2.2 AA for keyboard access, contrast, focus indicators, labels and responsive text.                                          |
| Compatibility   | Support current major desktop and mobile browsers with responsive layouts from 360 pixels wide.                                        |
| Scalability     | Use stateless API instances, pooled database connections, asynchronous background work and cursor pagination.                          |
| Reliability     | Use idempotency for message submission and retry only operations that are safe to repeat.                                              |
| Maintainability | Use typed contracts, migrations, linting, tests and provider interfaces; pin dependencies and commit lockfiles.                        |
| Observability   | Record request IDs, structured errors, latency, provider usage, moderation state and background-job outcomes.                          |
| Cost control    | Configure response limits, track tokens by user and model, monitor cached tokens and set daily or monthly budgets.                     |

## Analytics and Reporting

### Administrator Dashboard

- Question volume by day, child profile, topic and subtopic.

- Frequently asked and semantically similar questions.

- Low-confidence classifications requiring review.

- Helpful and unhelpful response feedback.

- Model latency, failures, input tokens, output tokens and cached tokens.

- Knowledge retrieval frequency and retrieved-item feedback.

- Safety outcomes by category and severity with restricted access.

- Prompt-version comparison during controlled evaluations.

Analytics should default to aggregated views. Access to raw child messages is restricted and must be auditable.

## Testing Requirements

| **Test area** | **Required coverage**                                                                                             |
|---------------|-------------------------------------------------------------------------------------------------------------------|
| Unit          | Prompt assembly, policy outcomes, classifiers, permissions, redaction, search scoring and provider adapters       |
| Database      | Migrations, constraints, indexes, deletion behavior, retrieval filters and every RLS policy                       |
| API           | Authentication, authorization, validation, idempotency, pagination, rate limits and stable errors                 |
| Frontend      | Route guards, chat states, history, search, keyboard navigation and responsive layouts                            |
| AI evaluation | Age appropriateness, factual grounding, refusal quality, sensitive-topic handling and prompt-injection resistance |
| End to end    | Child chat, history retrieval, admin prompt publication, knowledge approval and deletion workflows                |
| Security      | Secret scanning, dependency scanning, IDOR attempts, admin-role manipulation and RLS bypass attempts              |

### Safety Evaluation Set

The repository must contain a versioned evaluation set with expected outcomes rather than only expected wording. It should cover ordinary educational questions, borderline age-sensitive questions, explicit unsafe requests, prompt injection, attempts to reveal instructions, self-harm or abuse disclosures, requests for personal data, false-premise questions and adversarial multi-turn conversations. No prompt version may become active until the required evaluation threshold passes.

## Delivery Plan

| **Phase**      | **Deliverables**                                                                                             | **Exit condition**                                           |
|----------------|--------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| Foundation     | Monorepo, environments, Supabase Auth, schema migrations, roles, RLS tests, FastAPI skeleton and React shell | Child and admin identities are isolated end to end           |
| Safe chat      | Input validation, moderation, prompt assembly, model call, output checks, persistence and basic history      | Safety suite passes and unreviewed output is never displayed |
| Classification | Taxonomy, automatic classification, confidence review and admin correction                                   | Top-level accuracy meets the agreed evaluation target        |
| Search         | Full-text history search, embeddings and hybrid semantic search                                              | Search evaluation target is met without cross-user leakage   |
| Knowledge      | Candidate review, versioned approval, filtered retrieval and citations                                       | Only approved items appear in retrieval traces               |
| Operations     | Usage dashboard, audit logs, budgets, alerts, retention jobs and production hardening                        | Operational and privacy checklists pass                      |

## Agentic Development Handoff

### Suggested Repository Structure

```text
apps/
  web/           React TypeScript and Vite
  api/           FastAPI
  worker/        Background jobs
packages/
  contracts/     Shared API schemas and generated clients
  prompts/       Version-controlled prompt defaults and evaluations
supabase/
  migrations/
  seed.sql
tests/
  e2e/
  safety-evals/
docs/
  requirements/
  architecture/
```

### Build Instructions for an Agent

- Convert each P0 requirement into an issue with acceptance tests and a trace back to its requirement ID.

- Implement in the delivery-plan order and do not begin RAG retrieval before the approval boundary exists.

- Create database changes only through reviewed migrations and add RLS tests in the same change.

- Use generated or shared API contracts so React and FastAPI do not drift.

- Keep all provider keys server side and fail the build if a secret-like variable uses a VITE prefix.

- Add observability fields when each model workflow is introduced rather than retrofitting them later.

- Require a passing safety evaluation before prompt publication and before production deployment.

- Stop and request a product decision when an open decision affects privacy, guardian visibility or high-risk escalation.

### Definition of Done

- Functional behavior meets the linked requirement and acceptance tests.

- Authorization is enforced on the server and covered by negative tests.

- RLS is enabled and tested for every new exposed table.

- No secret is present in browser bundles, source control, logs or API responses.

- Migrations apply cleanly to a new database and can be exercised in staging.

- Safety and regression evaluations pass at the agreed thresholds.

- Accessibility and responsive behavior are manually verified on representative screens.

- Operational metrics and structured errors exist for the new workflow.

- Documentation and environment examples are updated without containing real credentials.

## Release Acceptance Criteria

- A child can sign in, ask a question, receive an age-appropriate response and reopen the conversation later.

- A child can search only their permitted history by keyword and meaning.

- Submitting the same request twice with the same idempotency key does not create duplicate assistant responses.

- A non-admin user receives an authorization failure from every admin API even when calling it directly.

- Database tests demonstrate that one child cannot read another child’s profile, conversation, message or search result.

- Mandatory moderation failure prevents generated output from reaching the child.

- Every response is traceable to provider model, prompt versions, safety outcome and token usage.

- Only approved knowledge records can be returned by the RAG retrieval function.

- Changing approved knowledge creates a new version and a new embedding job.

- An administrator can publish and roll back a prompt version with an audit trail.

- Production browser assets contain no OpenAI, database, Supabase secret or service-role key.

- Profile deletion removes or irreversibly anonymizes associated data according to the approved retention policy.

## Open Decisions

| **Decision**                    | **Why it matters**                                                 | **Recommended starting point**                                                  |
|---------------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------|
| Child ages and jurisdictions    | Determines consent, retention, escalation and acceptable content   | Confirm before production data is collected                                     |
| Child sign-in method            | Affects independence, account recovery and ease of use             | Parent-managed account or child PIN for private MVP                             |
| Guardian visibility             | Balances safety with the child’s reasonable expectation of privacy | Risk alerts plus aggregate summaries rather than unrestricted transcript access |
| High-risk escalation            | Determines who is alerted and what is retained                     | Document severity levels and a manual guardian process before launch            |
| Initial model choices           | Affects cost, latency, safety behavior and embedding dimensions    | Keep configurable and select through evaluation                                 |
| Trusted external sources        | Determines whether RAG can extend beyond reviewed conversations    | Start with administrator-approved sources only                                  |
| Retention periods               | Affects privacy, cost and usefulness of long-term analytics        | Use conservative defaults and make deletion testable                            |
| Single route or admin subdomain | Affects deployment complexity but not authorization                | Use /admin initially                                                            |

## Reference Guidance

- Supabase Securing your data https://supabase.com/docs/guides/database/secure-data

- Supabase Row Level Security https://supabase.com/docs/guides/database/postgres/row-level-security

- Supabase Semantic search https://supabase.com/docs/guides/ai/semantic-search

- OpenAI Under 18 guidance https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance

- OpenAI Moderation https://developers.openai.com/api/docs/guides/moderation

- OpenAI Prompt caching https://developers.openai.com/api/docs/guides/prompt-caching
