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
LAST_PARSED_QUERY: Dict[str, Any] = {}


class QueryRequest(BaseModel):
    query: str


def _query_plan_description(plan: Dict[str, Any]) -> str:
    plan_type = plan.get("type")
    entity = plan.get("entity", "entity")
    if plan_type == "aggregation":
        metric = plan.get("metric", "metric")
        group_by = plan.get("group_by", "group")
        return f"Aggregate {entity} by {group_by} using {metric}."
    if plan_type == "traversal":
        path = plan.get("path") or []
        if isinstance(path, list) and path:
            return f"Traverse process path: {' -> '.join(str(step) for step in path)}."
        return f"Traverse graph relationships from {entity}."
    if plan_type == "anomaly_detection":
        condition = plan.get("condition", "anomaly condition")
        return f"Detect anomalies on {entity} using condition '{condition}'."
    return "Resolve ERP query using deterministic graph operations."


def _is_follow_up_query(user_query: str) -> bool:
    q = (user_query or "").strip().lower()
    follow_up_markers = ["this", "that", "same", "previous", "again", "it", "them", "those"]
    return any(token in q.split() for token in follow_up_markers)


def _apply_follow_up_memory(parsed_query: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    global LAST_PARSED_QUERY
    if not LAST_PARSED_QUERY:
        return parsed_query

    intent = parsed_query.get("intent")
    if intent == "unknown" and _is_follow_up_query(user_query):
        recovered = dict(LAST_PARSED_QUERY)
        recovered["follow_up"] = True
        return recovered

    if intent == LAST_PARSED_QUERY.get("intent"):
        merged = dict(parsed_query)
        for key in ("order_id", "invoice_id", "type", "limit"):
            if merged.get(key) is None and LAST_PARSED_QUERY.get(key) is not None:
                merged[key] = LAST_PARSED_QUERY[key]
        return merged

    return parsed_query


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
    global LAST_PARSED_QUERY
    start_time = time.time()

    user_query = (payload.query or "").strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    if GRAPH is None:
        raise HTTPException(status_code=503, detail="Graph is not loaded")

    try:
        print("User Query:", user_query)
        parsed_query = parse_query(user_query, provider="gemini")
        parsed_query = _apply_follow_up_memory(parsed_query, user_query)
        print("Parsed Query:", parsed_query)
        result = execute_query(GRAPH, parsed_query)
        print("Execution Result:", result)
        answer = format_response(parsed_query, result)
        highlight_nodes = result.get("data", {}).get("highlight_nodes", [])
        query_plan = result.get("data", {}).get("query_plan", {})
        if isinstance(query_plan, dict):
            query_plan = {
                **query_plan,
                "description": _query_plan_description(query_plan),
            }

        if parsed_query.get("intent") not in {"unknown", "rejected"}:
            LAST_PARSED_QUERY = dict(parsed_query)

        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)

        return {
            "parsed_query": parsed_query,
            "query_plan": query_plan,
            "result": result,
            "answer": answer,
            "highlight_nodes": highlight_nodes,
            "execution_time_ms": execution_time_ms,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")
