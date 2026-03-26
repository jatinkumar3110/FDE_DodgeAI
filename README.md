Important info for FDE_Dodge AI Team: Backend is hosted on Render free tier and may take ~20–30 seconds to wake up on first request.

# AI-Powered ERP O2C Graph Query System

## 1. Problem Statement
Enterprise Order-to-Cash data is operationally critical but structurally fragmented across many ERP entities, such as sales orders, deliveries, invoices, journal entries, and payments. In a traditional relational view, answering process-level questions often requires multi-step joins, table-level context, and domain expertise. This creates friction for both technical and business users.

Key pain points:
- Data is distributed across multiple datasets with indirect relationships.
- End-to-end process traceability is difficult to perform manually.
- Querying requires schema knowledge, not business language.

This project addresses those gaps by combining graph modeling with natural language intent parsing so users can ask ERP questions directly.

## 2. Solution Overview
The solution transforms raw ERP JSONL files into a connected graph and exposes a natural language query interface.

Core approach:
- Ingest and normalize ERP data from JSONL sources.
- Model process entities and relationships as a directed graph in NetworkX.
- Execute deterministic graph traversals for business queries.
- Use an LLM only to translate user language into structured intent.
- Serve results through a FastAPI backend and a React chat UI.

This architecture preserves deterministic, auditable data access while offering an intuitive interaction layer.

## 3. Architecture
The system is organized into six layers:

1. Data Layer
- Loads JSONL files recursively from the dataset root.
- Normalizes key fields, especially item identifiers.
- Produces entity-wise in-memory collections for graph construction.

2. Graph Layer
- Builds a directed graph using NetworkX.
- Creates typed nodes and relationship edges with metadata.
- Tracks missing or optional links safely without crashing.

3. Query Engine Layer
- Encapsulates graph traversal logic for core use cases.
- Returns structured JSON outputs for API consumption.
- Keeps query functions deterministic and testable.

4. LLM Layer
- Parses natural language into structured query intents.
- Uses Gemini (or Groq) via a strict JSON prompt template.
- Applies guardrails and heuristic fallback parsing.

5. API Layer
- Exposes query execution through FastAPI.
- Provides a health endpoint for operational checks.
- Returns parsed intent, execution result, natural language answer, and execution time.

6. UI Layer
- React single-page chat interface.
- Sends user prompts to backend query endpoint.
- Displays user message, system answer, and parsed intent details.

## 4. Data Modeling
### Node Types
- Order
- OrderItem
- Delivery
- DeliveryItem
- Invoice
- InvoiceItem
- JournalEntry
- Payment
- Customer
- Product
- Plant

### Edge Types
- Order -> OrderItem via HAS_ITEM
- OrderItem -> DeliveryItem via DELIVERED_IN
- DeliveryItem -> InvoiceItem via BILLED_IN
- Invoice -> JournalEntry via POSTED_AS
- Invoice -> Payment via PAID_BY
- Order -> Customer via ORDERED_BY
- OrderItem -> Product via OF_PRODUCT
- DeliveryItem -> Plant via FROM_PLANT

### Item-Level Modeling (Critical)
Item-level entities are modeled as first-class nodes, not flattened into header-level properties. This preserves process granularity and prevents incorrect joins when a single order or invoice has multiple line items.

Composite keys are used for line-level identity:
- OrderItem: salesOrder + salesOrderItem
- DeliveryItem: deliveryDocument + deliveryDocumentItem
- InvoiceItem: billingDocument + billingDocumentItem

### Optional Relationships
Some ERP relationships are process-dependent and not mandatory for every record. For example:
- Not every invoice has a payment at the same time.
- Cancellation references are conditional.

The graph builder treats these safely as optional and records missing relationship counts for visibility.

## 5. Key Design Decisions
### Why Graph Over Relational Joins
Graph traversal maps directly to process flow questions such as Order -> Delivery -> Invoice -> Payment. This reduces query complexity and improves readability for cross-entity process tracing.

### Why Item-Level Joins
Header-level joins alone can introduce ambiguity in many-to-many business events. Item-level linking ensures traceability at the transactional unit where ERP truth actually resides.

### Why LLM for Parsing Only
The LLM is used only for intent extraction, not for generating business answers. Actual answers come from deterministic graph traversals. This improves reliability, auditability, and consistency.

### Why Gemini
Gemini provides robust instruction-following for structured extraction workflows. The implementation is provider-aware and can also work with Groq, while preserving the same backend contract.

## 6. AI Usage
The AI layer is intentionally constrained:

- Intent Extraction
  - Converts natural language into a strict JSON intent schema.
  - Example: find_journal with invoice_id.

- Guardrails
  - Rejects unrelated prompts and returns a domain-specific response.
  - Prevents out-of-scope usage such as general chat requests.

- Structured Parsing
  - Enforces an allowed intent set.
  - Uses safe JSON extraction and validation.

- Heuristic Fallback
  - If model output is unavailable or malformed, deterministic parsing logic attempts recovery.

This design balances usability with production safety.

## 7. Features
- End-to-end order flow tracing across ERP lifecycle entities.
- Journal lookup by invoice.
- Detection of orders with delivery but no invoice.
- Top products analysis based on billing-linked flows.
- API-level execution time reporting.
- Health check endpoint for service monitoring.

## 8. Example Queries
Natural language queries supported:

- Trace order 740509
- Find journal for invoice 91150187
- Show orders without invoice
- Top 5 products by billing

## 9. Setup Instructions
### Backend
1. Create and activate a Python environment.
2. Install dependencies:
   - pip install fastapi uvicorn pydantic networkx google-generativeai
3. Start API server:
   - uvicorn main:app --reload

### Frontend
1. Install dependencies:
   - npm install
2. Start development server:
   - npm start

Backend base URL expected by UI:
- http://127.0.0.1:8000

## 10. API Endpoints
### POST /query
Request body:
{
  "query": "Find journal for invoice 91150187"
}

Response body:
{
  "parsed_query": { ... },
  "result": { ... },
  "answer": "...",
  "execution_time_ms": 42
}

### GET /health
Response body:
{
  "status": "ok",
  "graph_loaded": true
}

## 11. Challenges and Learnings
### Inconsistent Identifier Formats
ERP item IDs may differ in representation (for example 000010 vs 10). Normalization at ingestion is essential to maintain join correctness.

### Optional and Asynchronous Process Links
Financial posting and payment events may be delayed relative to billing. Modeling these as optional relationships avoids false negatives and system brittleness.

### Traversal Design Complexity
A reliable process query requires careful graph traversal strategy, especially when crossing item-level and header-level boundaries.

### LLM Reliability in Production
Unconstrained model responses can break downstream execution. Strict prompting, intent validation, and heuristic fallback are necessary for dependable behavior.

## 12. Future Improvements
- Migrate from in-memory NetworkX to Neo4j for persistence, scale, and Cypher analytics.
- Add role-based authentication and rate limiting for production API hardening.
- Improve UI with query history persistence and richer result visualization.
- Extend analytics with SLA metrics, payment lag analysis, and anomaly detection.
- Add automated tests for parser intents and traversal correctness.

## 13. Repository Structure
- [main.py](main.py): FastAPI service and API endpoints.
- [data_loader.py](data_loader.py): JSONL ingestion and normalization.
- [graph_builder.py](graph_builder.py): Graph construction logic.
- [query_engine.py](query_engine.py): Deterministic graph query functions.
- [llm_handler.py](llm_handler.py): LLM parsing, guardrails, dispatch, response formatting.
- [src/App.jsx](src/App.jsx): React chat UI.
- [src/index.js](src/index.js): React entrypoint.
- [src/styles.css](src/styles.css): Minimal UI styling.

## 14. Summary
This project demonstrates a practical pattern for enterprise AI systems: use LLMs for language understanding, and use deterministic graph computation for business truth. The result is a system that is intuitive for users, technically robust, and aligned with production engineering principles.
