from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from query_engine import (
    count_flow_entities,
    find_broken_flows,
    find_journal_by_invoice,
    find_orders_without_invoice,
    top_products_by_billing,
    trace_billing,
    trace_invoice_backward,
    trace_order_flow,
    trace_order_full,
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
    "trace_order_full",
    "trace_invoice_backward",
    "count_flow_entities",
    "multi_condition_query",
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
    "trace_order_full": [
        "trace order full",
        "trace full order",
        "end to end order",
        "full order journey",
    ],
    "trace_invoice_backward": [
        "originating order",
        "trace backward",
        "invoice backward trace",
        "invoice to order",
    ],
    "count_flow_entities": [
        "how many deliveries",
        "count invoices",
        "count deliveries and invoices",
        "delivery and invoice count",
    ],
    "orders_without_invoice": [
        "orders without invoice",
        "order has delivery but no invoice",
        "missing invoice orders",
    ],
    "top_products": [
        "top products by billing",
        "highest billed products",
        "highest billing products",
        "which products have highest billing",
        "which products have most invoices",
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
        "broken orders",
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

    allowed_keywords = {
        "order",
        "orders",
        "invoice",
        "invoices",
        "delivery",
        "deliveries",
        "billing",
        "product",
        "products",
        "payment",
        "payments",
        "journal",
    }
    tokens = set(normalized.split())
    return len(tokens.intersection(allowed_keywords)) == 0


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


def _split_multi_query(user_query: str) -> List[str]:
    text = user_query.strip()
    if not text or " and " not in text.lower():
        return []

    parts = [part.strip(" ,.;") for part in re.split(r"\band\b", text, flags=re.IGNORECASE)]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return []
    return parts


def _heuristic_parse(user_query: str) -> JSONDict:
    q = _normalize_text(user_query)

    if "journal" in q and "invoice" in q:
        invoice = _extract_identifier(user_query)
        if invoice:
            return {"intent": "find_journal", "invoice_id": invoice}

    if ("trace" in q and "order" in q) or "trace order" in q:
        order_id = _extract_identifier(user_query)
        if order_id:
            if "full" in q or "end to end" in q:
                return {"intent": "trace_order_full", "order_id": order_id}
            return {"intent": "trace_order", "order_id": order_id}

    if "trace" in q and ("backward" in q or "originating" in q) and "invoice" in q:
        invoice_id = _extract_identifier(user_query)
        if invoice_id:
            return {"intent": "trace_invoice_backward", "invoice_id": invoice_id}

    if ("how many" in q or "count" in q) and (
        "delivery" in q or "deliveries" in q or "invoice" in q or "invoices" in q
    ):
        order_id = _extract_identifier(user_query)
        if order_id:
            return {"intent": "count_flow_entities", "order_id": order_id}

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

    # Explicit semantic mappings first.
    if "how many deliveries" in normalized_query or "count invoices" in normalized_query:
        order_id = _extract_identifier(user_query)
        return {"intent": "count_flow_entities", "order_id": order_id} if order_id else {"intent": "unknown"}

    if "trace order" in normalized_query:
        order_id = _extract_identifier(user_query)
        return {"intent": "trace_order_full", "order_id": order_id} if order_id else {"intent": "unknown"}

    if "originating order" in normalized_query or "trace backward" in normalized_query:
        invoice_id = _extract_identifier(user_query)
        return {"intent": "trace_invoice_backward", "invoice_id": invoice_id} if invoice_id else {"intent": "unknown"}

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

    if best_intent in {"trace_order", "trace_order_full"}:
        order_id = _extract_identifier(user_query)
        return {"intent": best_intent, "order_id": order_id} if order_id else {"intent": "unknown"}

    if best_intent == "trace_invoice_backward":
        invoice_id = _extract_identifier(user_query)
        return {"intent": "trace_invoice_backward", "invoice_id": invoice_id} if invoice_id else {"intent": "unknown"}

    if best_intent == "count_flow_entities":
        order_id = _extract_identifier(user_query)
        return {"intent": "count_flow_entities", "order_id": order_id} if order_id else {"intent": "unknown"}

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
    if parsed.get("queries") is not None and isinstance(parsed.get("queries"), list):
        clean["queries"] = [q for q in parsed.get("queries") if isinstance(q, dict)]
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
3. trace_order_full -> requires order_id
4. trace_invoice_backward -> requires invoice_id
5. count_flow_entities -> requires order_id
6. orders_without_invoice -> no params
7. top_products -> optional limit
8. trace_billing -> requires invoice_id when present in query
9. broken_flows -> requires type:
    - delivered_not_billed
    - billed_without_delivery

If query is unrelated -> return:
{{"intent": "unknown"}}

User Query:
{user_query}
"""


def _parse_single_query(user_query: str, provider: str = "groq") -> JSONDict:
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


def parse_query(user_query: str, provider: str = "groq") -> JSONDict:
    if _is_rejected_query(user_query):
        return {
            "intent": "rejected",
            "message": GUARDRAIL_MESSAGE,
        }

    parts = _split_multi_query(user_query)
    if parts:
        parsed_parts = [_parse_single_query(part, provider=provider) for part in parts]
        parsed_parts = [part for part in parsed_parts if part.get("intent") not in {"unknown", "rejected"}]
        if len(parsed_parts) >= 2:
            return {
                "intent": "multi_condition_query",
                "queries": parsed_parts,
            }

    return _parse_single_query(user_query, provider=provider)


def execute_query(graph: Any, parsed_query: JSONDict) -> JSONDict:
    query_plan = plan_query(parsed_query)

    def _attach_plan(result: JSONDict) -> JSONDict:
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            data = {}
        data["query_plan"] = query_plan
        result["data"] = data
        return result

    def _execute_single(single_query: JSONDict) -> JSONDict:
        intent = (single_query or {}).get("intent")

        if intent == "rejected":
            return {
                "ok": False,
                "message": GUARDRAIL_MESSAGE,
                "data": {},
            }

        if intent == "find_journal":
            invoice_id = single_query.get("invoice_id")
            if not invoice_id:
                return {
                    "ok": False,
                    "message": "Please provide a billing document or invoice ID. Example: 'Find journal for invoice 91150187'",
                    "data": {},
                }
            return find_journal_by_invoice(graph, str(invoice_id))

        if intent in {"trace_order", "trace_order_full"}:
            order_id = single_query.get("order_id")
            if not order_id:
                return {"ok": False, "message": "order_id is required", "data": {}}
            if intent == "trace_order_full":
                return trace_order_full(graph, str(order_id))
            return trace_order_flow(graph, str(order_id))

        if intent == "trace_invoice_backward":
            invoice_id = single_query.get("invoice_id")
            if not invoice_id:
                return {
                    "ok": False,
                    "message": "Please specify invoice ID. Example: Trace invoice backward 91150187",
                    "data": {},
                }
            return trace_invoice_backward(graph, str(invoice_id))

        if intent == "count_flow_entities":
            order_id = single_query.get("order_id")
            if not order_id:
                return {
                    "ok": False,
                    "message": "Please specify order ID. Example: How many deliveries and invoices for order 4745",
                    "data": {},
                }
            return count_flow_entities(graph, str(order_id))

        if intent == "orders_without_invoice":
            return find_orders_without_invoice(graph)

        if intent == "top_products":
            raw_limit = single_query.get("limit", 5)
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                limit = 5
            if limit < 1:
                limit = 5
            return top_products_by_billing(graph, limit=limit)

        if intent == "trace_billing":
            invoice_id = single_query.get("invoice_id")
            if not invoice_id:
                return {
                    "ok": False,
                    "message": "Please specify invoice ID. Example: Trace billing 91150187",
                    "data": {},
                }
            return trace_billing(graph, str(invoice_id))

        if intent == "broken_flows":
            flow_type = single_query.get("type")
            if flow_type not in {"delivered_not_billed", "billed_without_delivery"}:
                return {
                    "ok": False,
                    "message": "type must be delivered_not_billed or billed_without_delivery",
                    "data": {},
                }
            return find_broken_flows(graph, str(flow_type))

        return {"ok": False, "message": GUARDRAIL_MESSAGE, "data": {}}

    intent = (parsed_query or {}).get("intent")
    if intent == "multi_condition_query":
        queries = parsed_query.get("queries") if isinstance(parsed_query, dict) else None
        if not isinstance(queries, list) or len(queries) < 2:
            return _attach_plan({"ok": False, "message": "No valid sub-queries found", "data": {}})

        sub_results: List[JSONDict] = []
        merged_highlight_nodes: List[str] = []
        all_ok = True

        for index, query_part in enumerate(queries):
            result = _execute_single(query_part)
            sub_results.append(
                {
                    "index": index + 1,
                    "parsed_query": query_part,
                    "result": result,
                }
            )
            if not result.get("ok"):
                all_ok = False
            result_nodes = result.get("data", {}).get("highlight_nodes", [])
            if isinstance(result_nodes, list):
                merged_highlight_nodes.extend(str(node) for node in result_nodes)

        # Preserve order while deduplicating for deterministic rendering.
        dedup_highlights: List[str] = []
        seen = set()
        for node in merged_highlight_nodes:
            if node in seen:
                continue
            seen.add(node)
            dedup_highlights.append(node)

        merged_payload = {
            "sub_results": sub_results,
            "sub_query_count": len(sub_results),
            "highlight_nodes": dedup_highlights,
            "highlight_node_count": len(dedup_highlights),
        }
        status_message = "Multi-condition query executed" if all_ok else "Multi-condition query partially completed"
        return _attach_plan({"ok": all_ok, "message": status_message, "data": merged_payload})

    return _attach_plan(_execute_single(parsed_query))


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
            return f"No journal entries found for invoice {invoice_id} in this dataset."
        ids = [entry.get("accountingDocument") for entry in journals if entry.get("accountingDocument")]
        return f"Invoice {invoice_id} maps to {len(journals)} journal entr{'y' if len(journals) == 1 else 'ies'}: {', '.join(ids)}."

    if intent in {"trace_order", "trace_order_full"}:
        return (
            f"Order {data.get('order_id')} has {data.get('delivery_count', 0)} deliveries, "
            f"{data.get('invoice_count', 0)} invoices, {data.get('journal_count', 0)} journals, "
            f"and {data.get('payment_count', 0)} payments."
        )

    if intent == "trace_invoice_backward":
        return (
            f"Invoice {data.get('invoice_id')} maps backward to {data.get('order_count', 0)} orders "
            f"through {data.get('delivery_count', 0)} deliveries."
        )

    if intent == "count_flow_entities":
        return (
            f"Order {data.get('order_id')} has {data.get('deliveries', 0)} deliveries "
            f"and {data.get('invoices', 0)} invoices."
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

    if intent == "multi_condition_query":
        sub_results = data.get("sub_results", [])
        completed = sum(1 for row in sub_results if row.get("result", {}).get("ok"))
        return f"Executed {completed}/{len(sub_results)} requested conditions and merged the results."

    return GUARDRAIL_MESSAGE
