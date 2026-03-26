from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from query_engine import (
    find_broken_flows,
    find_journal_by_invoice,
    find_orders_without_invoice,
    top_products_by_billing,
    trace_billing,
    trace_order_flow,
)
from query_planner import plan_query


JSONDict = Dict[str, Any]

GUARDRAIL_MESSAGE = "This system is designed to answer ERP dataset queries only."

ALLOWED_INTENTS = {
    "find_journal",
    "trace_order",
    "orders_without_invoice",
    "top_products",
    "trace_billing",
    "broken_flows",
}

INTENT_PHRASES = {
    "find_journal": [
        "find journal for invoice",
        "journal entry for invoice",
        "invoice posting",
        "journal for billing",
    ],
    "trace_order": [
        "trace order",
        "order flow",
        "order lifecycle",
        "order to cash trace",
    ],
    "orders_without_invoice": [
        "orders without invoice",
        "order has delivery but no invoice",
        "missing invoice orders",
    ],
    "top_products": [
        "top products by billing",
        "highest billed products",
        "which products have highest billing",
        "top invoice products",
    ],
    "trace_billing": [
        "trace billing",
        "invoice flow",
        "show invoice flow",
        "billing document flow",
    ],
    "broken_flows": [
        "broken flow",
        "delivered not billed",
        "billed without delivery",
        "flow anomaly",
    ],
}


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _extract_json_object(text: str) -> Optional[JSONDict]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()


def _is_rejected_query(user_query: str) -> bool:
    normalized = _normalize_text(user_query)
    if not normalized:
        return True

    erp_keywords = {
        "order",
        "invoice",
        "journal",
        "payment",
        "delivery",
        "product",
        "billing",
        "customer",
        "flow",
        "erp",
    }
    tokens = set(normalized.split())
    return len(tokens.intersection(erp_keywords)) == 0


def _extract_identifier(text: str) -> Optional[str]:
    tokens = re.findall(r"[A-Za-z0-9_-]+", text)
    candidates = [token for token in tokens if any(ch.isdigit() for ch in token)]
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


def _similarity_score(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _heuristic_parse(user_query: str) -> JSONDict:
    q = _normalize_text(user_query)

    if "journal" in q and "invoice" in q:
        invoice = _extract_identifier(user_query)
        if invoice:
            return {"intent": "find_journal", "invoice_id": invoice}

    if "trace" in q and "order" in q:
        order_id = _extract_identifier(user_query)
        if order_id:
            return {"intent": "trace_order", "order_id": order_id}

    if "trace" in q and ("billing" in q or "invoice" in q or "flow" in q):
        invoice_id = _extract_identifier(user_query)
        if invoice_id:
            return {"intent": "trace_billing", "invoice_id": invoice_id}
        return {"intent": "trace_billing"}

    if "broken" in q and "flow" in q:
        if "delivered" in q and "not" in q and "billed" in q:
            return {"intent": "broken_flows", "type": "delivered_not_billed"}
        if "billed" in q and "without" in q and "delivery" in q:
            return {"intent": "broken_flows", "type": "billed_without_delivery"}
        return {"intent": "broken_flows", "type": "delivered_not_billed"}

    if "without invoice" in q or ("no invoice" in q and "order" in q):
        return {"intent": "orders_without_invoice"}

    if ("top" in q or "highest" in q) and "product" in q and ("billing" in q or "invoice" in q):
        limit = _extract_limit(user_query)
        out: JSONDict = {"intent": "top_products"}
        if limit is not None:
            out["limit"] = limit
        return out

    return {"intent": "unknown"}


def _keyword_similarity_parse(user_query: str) -> JSONDict:
    normalized_query = _normalize_text(user_query)
    if not normalized_query:
        return {"intent": "unknown"}

    best_intent = "unknown"
    best_score = 0.0

    for intent, phrases in INTENT_PHRASES.items():
        for phrase in phrases:
            score = _similarity_score(normalized_query, _normalize_text(phrase))
            if phrase in normalized_query:
                score = max(score, 0.95)
            if score > best_score:
                best_score = score
                best_intent = intent

    if best_score < 0.48:
        return {"intent": "unknown"}

    if best_intent == "find_journal":
        invoice_id = _extract_identifier(user_query)
        return {"intent": "find_journal", "invoice_id": invoice_id} if invoice_id else {"intent": "unknown"}

    if best_intent == "trace_order":
        order_id = _extract_identifier(user_query)
        return {"intent": "trace_order", "order_id": order_id} if order_id else {"intent": "unknown"}

    if best_intent == "trace_billing":
        invoice_id = _extract_identifier(user_query)
        return {"intent": "trace_billing", "invoice_id": invoice_id} if invoice_id else {"intent": "trace_billing"}

    if best_intent == "top_products":
        limit = _extract_limit(user_query)
        out: JSONDict = {"intent": "top_products"}
        if limit is not None:
            out["limit"] = limit
        return out

    if best_intent == "orders_without_invoice":
        return {"intent": "orders_without_invoice"}

    if best_intent == "broken_flows":
        q = _normalize_text(user_query)
        if "billed" in q and "without" in q and "delivery" in q:
            return {"intent": "broken_flows", "type": "billed_without_delivery"}
        return {"intent": "broken_flows", "type": "delivered_not_billed"}

    return {"intent": "unknown"}


def _sanitize_parsed(parsed: Optional[JSONDict]) -> JSONDict:
    if not isinstance(parsed, dict):
        return {"intent": "unknown"}

    intent = parsed.get("intent")
    if intent not in ALLOWED_INTENTS and intent != "unknown":
        return {"intent": "unknown"}

    clean: JSONDict = {"intent": intent or "unknown"}
    if parsed.get("invoice_id") is not None:
        clean["invoice_id"] = str(parsed.get("invoice_id"))
    if parsed.get("order_id") is not None:
        clean["order_id"] = str(parsed.get("order_id"))
    if parsed.get("type") in {"delivered_not_billed", "billed_without_delivery"}:
        clean["type"] = parsed.get("type")
    if parsed.get("limit") is not None:
        try:
            clean["limit"] = int(parsed.get("limit"))
        except (TypeError, ValueError):
            pass
    return clean


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
5. trace_billing -> requires invoice_id when present in query
6. broken_flows -> requires type:
    - delivered_not_billed
    - billed_without_delivery

If query is unrelated -> return:
{{"intent": "unknown"}}

Examples:
Query: Which products have highest billing
Output: {{"intent": "top_products"}}

Query: show invoice flow
Output: {{"intent": "trace_billing"}}

User Query:
{user_query}
"""


def parse_query(user_query: str, provider: str = "groq") -> JSONDict:
    if _is_rejected_query(user_query):
        return {
            "intent": "rejected",
            "message": GUARDRAIL_MESSAGE,
        }

    parsed: Optional[JSONDict] = None
    provider_norm = (provider or "").strip().lower()

    if provider_norm == "groq":
        parsed = _query_groq(user_query)
    elif provider_norm == "gemini":
        parsed = _query_gemini(user_query)

    sanitized = _sanitize_parsed(parsed)

    if sanitized.get("intent") == "unknown":
        sanitized = _sanitize_parsed(_heuristic_parse(user_query))

    if sanitized.get("intent") == "unknown":
        sanitized = _sanitize_parsed(_keyword_similarity_parse(user_query))

    return sanitized


def execute_query(graph: Any, parsed_query: JSONDict) -> JSONDict:
    intent = (parsed_query or {}).get("intent")
    query_plan = plan_query(parsed_query)

    def _attach_plan(result: JSONDict) -> JSONDict:
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            data = {}
        data["query_plan"] = query_plan
        result["data"] = data
        return result

    if intent == "rejected":
        return _attach_plan({
            "ok": False,
            "message": GUARDRAIL_MESSAGE,
            "data": {},
        })

    if intent == "find_journal":
        invoice_id = parsed_query.get("invoice_id")
        if not invoice_id:
            return _attach_plan({"ok": False, "message": "invoice_id is required", "data": {}})
        return _attach_plan(find_journal_by_invoice(graph, str(invoice_id)))

    if intent == "trace_order":
        order_id = parsed_query.get("order_id")
        if not order_id:
            return _attach_plan({"ok": False, "message": "order_id is required", "data": {}})
        return _attach_plan(trace_order_flow(graph, str(order_id)))

    if intent == "orders_without_invoice":
        return _attach_plan(find_orders_without_invoice(graph))

    if intent == "top_products":
        raw_limit = parsed_query.get("limit", 5)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 5
        if limit < 1:
            limit = 5
        return _attach_plan(top_products_by_billing(graph, limit=limit))

    if intent == "trace_billing":
        invoice_id = parsed_query.get("invoice_id")
        if not invoice_id:
            return _attach_plan({"ok": False, "message": "invoice_id is required", "data": {}})
        return _attach_plan(trace_billing(graph, str(invoice_id)))

    if intent == "broken_flows":
        flow_type = parsed_query.get("type")
        if flow_type not in {"delivered_not_billed", "billed_without_delivery"}:
            return _attach_plan(
                {
                    "ok": False,
                    "message": "type must be delivered_not_billed or billed_without_delivery",
                    "data": {},
                }
            )
        return _attach_plan(find_broken_flows(graph, str(flow_type)))

    return _attach_plan({"ok": False, "message": GUARDRAIL_MESSAGE, "data": {}})


def format_response(parsed_query: JSONDict, execution_result: JSONDict) -> str:
    intent = (parsed_query or {}).get("intent")

    if intent == "rejected":
        return GUARDRAIL_MESSAGE

    ok = bool((execution_result or {}).get("ok"))
    data = (execution_result or {}).get("data", {}) or {}

    if not ok:
        message = (execution_result or {}).get("message", "Query failed")
        if message == GUARDRAIL_MESSAGE:
            return GUARDRAIL_MESSAGE
        return f"Could not complete the query: {message}."

    if intent == "find_journal":
        invoice_id = data.get("invoice_id")
        journals = data.get("journal_entries", [])
        if not journals:
            return f"Invoice {invoice_id} has no journal entries in this dataset."
        ids = [entry.get("accountingDocument") for entry in journals if entry.get("accountingDocument")]
        return f"Invoice {invoice_id} maps to {len(journals)} journal entr{'y' if len(journals) == 1 else 'ies'}: {', '.join(ids)}."

    if intent == "trace_order":
        return (
            f"Order {data.get('order_id')} has {data.get('delivery_count', 0)} deliveries, "
            f"{data.get('invoice_count', 0)} invoices, {data.get('journal_count', 0)} journals, "
            f"and {data.get('payment_count', 0)} payments."
        )

    if intent == "orders_without_invoice":
        count = data.get("count", 0)
        return f"Found {count} order{'s' if count != 1 else ''} with delivery activity but no invoice link."

    if intent == "top_products":
        top_products = data.get("top_products", [])
        if not top_products:
            return "No billed products were found for aggregation."
        preview = ", ".join(
            f"{product.get('product_id')} ({product.get('invoice_line_count')})"
            for product in top_products[:5]
        )
        return f"Top billed products by invoice-line frequency: {preview}."

    if intent == "trace_billing":
        return (
            f"Invoice {data.get('invoice_id')} touches {data.get('delivery_count', 0)} deliveries, "
            f"{data.get('order_count', 0)} orders, {data.get('journal_count', 0)} journals, "
            f"and {data.get('payment_count', 0)} payments."
        )

    if intent == "broken_flows":
        flow_type = data.get("type")
        count = data.get("count", 0)
        return f"Detected {count} issue item{'s' if count != 1 else ''} for broken flow type '{flow_type}'."

    return GUARDRAIL_MESSAGE
