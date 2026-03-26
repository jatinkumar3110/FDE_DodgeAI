from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph_builder import build_o2c_graph_from_path
from llm_handler import execute_query, format_response, parse_query


DATASET_PATH = "./sap-order-to-cash-dataset"
GRAPH = None


class QueryRequest(BaseModel):
    query: str


app = FastAPI(title="ERP O2C Query API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    global GRAPH
    GRAPH = build_o2c_graph_from_path(DATASET_PATH)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "graph_loaded": GRAPH is not None,
    }


@app.get("/graph")
def graph_endpoint() -> Dict[str, Any]:
    if GRAPH is None:
        raise HTTPException(status_code=503, detail="Graph is not loaded")

    nodes = []
    for node_id, attrs in GRAPH.nodes(data=True):
        node_type = attrs.get("node_type", "Unknown")
        node_key = attrs.get("key") or str(node_id)
        nodes.append(
            {
                "id": str(node_id),
                "label": str(node_key),
                "type": node_type,
                "source_entity": attrs.get("source_entity"),
            }
        )

    links = [
        {
            "source": str(source),
            "target": str(target),
        }
        for source, target in GRAPH.edges()
    ]

    return {
        "nodes": nodes,
        "links": links,
    }


@app.post("/query")
def query_endpoint(payload: QueryRequest) -> Dict[str, Any]:
    start_time = time.time()

    user_query = (payload.query or "").strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    if GRAPH is None:
        raise HTTPException(status_code=503, detail="Graph is not loaded")

    try:
        print("User Query:", user_query)
        parsed_query = parse_query(user_query, provider="gemini")
        print("Parsed Query:", parsed_query)
        result = execute_query(GRAPH, parsed_query)
        print("Execution Result:", result)
        answer = format_response(parsed_query, result)
        highlight_nodes = result.get("data", {}).get("highlight_nodes", [])

        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)

        return {
            "parsed_query": parsed_query,
            "result": result,
            "answer": answer,
            "highlight_nodes": highlight_nodes,
            "execution_time_ms": execution_time_ms,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")
