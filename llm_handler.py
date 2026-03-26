from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from query_engine import (
    find_journal_by_invoice,
    find_orders_without_invoice,
    top_products_by_billing,
    trace_order_flow,
)


JSONDict = Dict[str, Any]


ALLOWED_INTENTS = {
    "find_journal",
    "trace_order",
    "orders_without_invoice",
    "top_products",
}


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _extract_json_object(text: str) -> Optional[JSONDict]:
    # Pull first JSON object from model text to tolerate extra prose.
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _is_rejected_query(user_query: str) -> bool:
    q = (user_query or "").strip().lower()
    if not q:
        return True

    blocked_patterns = [
        r"\bwho\s+is\s+pm\b",
        r"\bwrite\s+(a\s+)?poem\b",
        r"\bpoem\b",
        r"\bjoke\b",
        r"\bstory\b",
        r"\bweather\b",
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, q):
            return True

    erp_signals = [
        "order",
        "invoice",
        "journal",
        "payment",
        "delivery",
        "product",
        "billing",
        "customer",
    ]
    return not any(token in q for token in erp_signals)


def _heuristic_parse(user_query: str) -> JSONDict:
    q = (user_query or "").lower()

    if "journal" in q and "invoice" in q:
        invoice = _extract_identifier(user_query)
        if invoice:
            return {"intent": "find_journal", "invoice_id": invoice}

    if "trace" in q and "order" in q:
        order_id = _extract_identifier(user_query)
        if order_id:
            return {"intent": "trace_order", "order_id": order_id}

    if "without invoice" in q or ("no invoice" in q and "order" in q):
        return {"intent": "orders_without_invoice"}

    if "top" in q and "product" in q and ("billing" in q or "invoice" in q):
        limit = _extract_limit(user_query)
        out: JSONDict = {"intent": "top_products"}
        if limit is not None:
            out["limit"] = limit
        return out

    return {"intent": "unknown"}


def _extract_identifier(text: str) -> Optional[str]:
    tokens = re.findall(r"[A-Za-z0-9_-]+", text)
    candidates = [t for t in tokens if any(ch.isdigit() for ch in t)]
    if not candidates:
        return None
    return candidates[-1]


def _extract_limit(text: str) -> Optional[int]:
    nums = re.findall(r"\d+", text)
    if not nums:
        return None
    try:
        return int(nums[-1])
    except ValueError:
        return None


def _query_groq(user_query: str, model: str = "llama-3.1-8b-instant") -> Optional[JSONDict]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    prompt = _prompt_template(user_query)
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You convert ERP graph queries into strict JSON."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = _post_json("https://api.groq.com/openai/v1/chat/completions", headers, payload)
        text = resp["choices"][0]["message"]["content"]
        return _extract_json_object(text)
    except (KeyError, IndexError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _query_gemini(user_query: str, model: str = "gemini-1.5-flash") -> Optional[JSONDict]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = _prompt_template(user_query)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = _post_json(url, headers, payload)
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json_object(text)
    except (KeyError, IndexError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _prompt_template(user_query: str) -> str:
    return f"""
You are an ERP query parser.

STRICT RULES:
- Output ONLY valid JSON
- No explanation, no text outside JSON
- Do NOT hallucinate fields

Allowed intents:
1. find_journal -> requires invoice_id
2. trace_order -> requires order_id
3. orders_without_invoice -> no params
4. top_products -> optional limit

If query is unrelated -> return:
{{"intent": "unknown"}}

Examples:

Query: Find journal for invoice 91150187
Output: {{"intent": "find_journal", "invoice_id": "91150187"}}

Query: Trace order 740509
Output: {{"intent": "trace_order", "order_id": "740509"}}

Query: Show orders without invoice
Output: {{"intent": "orders_without_invoice"}}

Query: Top 5 products by billing
Output: {{"intent": "top_products", "limit": 5}}

User Query:
{user_query}
"""


def parse_query(user_query: str, provider: str = "groq") -> JSONDict:
    """Parse natural language into structured query JSON.

    provider: "groq" or "gemini"
    Falls back to heuristic parser if LLM is unavailable or fails.
    """
    if _is_rejected_query(user_query):
        return {
            "intent": "rejected",
            "message": "This system only answers ERP dataset queries",
        }

    parsed: Optional[JSONDict] = None
    provider_norm = (provider or "").strip().lower()

    if provider_norm == "groq":
        parsed = _query_groq(user_query)
    elif provider_norm == "gemini":
        parsed = _query_gemini(user_query)

    if not parsed:
        parsed = _heuristic_parse(user_query)

    intent = parsed.get("intent") if isinstance(parsed, dict) else None
    if intent not in ALLOWED_INTENTS and intent != "unknown":
        return {"intent": "unknown"}

    return parsed


def execute_query(graph: Any, parsed_query: JSONDict) -> JSONDict:
    """Dispatch parsed query to query_engine functions."""
    intent = (parsed_query or {}).get("intent")

    if intent == "rejected":
        return {
            "ok": False,
            "message": "This system only answers ERP dataset queries",
            "data": {},
        }

    if intent == "find_journal":
        invoice_id = parsed_query.get("invoice_id")
        if not invoice_id:
            return {"ok": False, "message": "invoice_id is required", "data": {}}
        return find_journal_by_invoice(graph, str(invoice_id))

    if intent == "trace_order":
        order_id = parsed_query.get("order_id")
        if not order_id:
            return {"ok": False, "message": "order_id is required", "data": {}}
        return trace_order_flow(graph, str(order_id))

    if intent == "orders_without_invoice":
        return find_orders_without_invoice(graph)

    if intent == "top_products":
        raw_limit = parsed_query.get("limit", 10)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 10
        if limit < 1:
            limit = 10
        return top_products_by_billing(graph, limit=limit)

    return {"ok": False, "message": "Unsupported ERP query", "data": {}}


def format_response(parsed_query: JSONDict, execution_result: JSONDict) -> str:
    """Convert structured execution output into concise natural language."""
    intent = (parsed_query or {}).get("intent")

    if intent == "rejected":
        return "This system only answers ERP dataset queries"

    ok = bool((execution_result or {}).get("ok"))
    data = (execution_result or {}).get("data", {}) or {}

    if not ok:
        msg = (execution_result or {}).get("message", "Query failed")
        return f"Could not complete the query: {msg}."

    if intent == "find_journal":
        invoice_id = data.get("invoice_id")
        journals = data.get("journal_entries", [])
        if not journals:
            return f"No journal entry found for invoice {invoice_id}."
        ids = [j.get("accountingDocument") for j in journals if j.get("accountingDocument")]
        return f"Found {len(journals)} journal entr{'y' if len(journals)==1 else 'ies'} for invoice {invoice_id}: {', '.join(ids)}."

    if intent == "trace_order":
        order_id = data.get("order_id")
        return (
            f"Order {order_id} flow: {data.get('delivery_count', 0)} deliveries, "
            f"{data.get('invoice_count', 0)} invoices, "
            f"{data.get('journal_count', 0)} journal entries, "
            f"{data.get('payment_count', 0)} payments."
        )

    if intent == "orders_without_invoice":
        count = data.get("count", 0)
        return f"Found {count} orders that have delivery but no invoice."

    if intent == "top_products":
        top_products = data.get("top_products", [])
        if not top_products:
            return "No billed products were found."
        preview = ", ".join(
            f"{p.get('product_id')} ({p.get('invoice_line_count')})" for p in top_products[:5]
        )
        return f"Top billed products: {preview}."

    return "This system only answers ERP dataset queries"
