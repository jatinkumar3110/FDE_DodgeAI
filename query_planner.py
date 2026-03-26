from __future__ import annotations

from typing import Any, Dict


JSONDict = Dict[str, Any]


def plan_query(parsed_query: JSONDict) -> JSONDict:
    """Translate parsed intent into a simple deterministic query plan."""
    intent = (parsed_query or {}).get("intent")

    if intent == "find_journal":
        return {
            "type": "traversal",
            "entity": "Invoice",
            "path": ["Invoice", "JournalEntry"],
            "relation": "POSTED_AS",
        }

    if intent == "trace_order":
        return {
            "type": "flow_trace",
            "entity": "Order",
            "path": ["Order", "Delivery", "Invoice", "JournalEntry", "Payment"],
        }

    if intent == "orders_without_invoice":
        return {
            "type": "anomaly_detection",
            "entity": "Order",
            "condition": "has_delivery_and_no_invoice",
        }

    if intent == "top_products":
        return {
            "type": "aggregation",
            "entity": "InvoiceItem",
            "group_by": "product_id",
            "metric": "count",
            "limit": parsed_query.get("limit", 5),
        }

    if intent == "trace_billing":
        return {
            "type": "flow_trace",
            "entity": "Invoice",
            "path": ["Invoice", "Delivery", "Order", "JournalEntry", "Payment"],
        }

    if intent == "broken_flows":
        return {
            "type": "anomaly_detection",
            "entity": "Flow",
            "condition": parsed_query.get("type", "unknown"),
        }

    return {
        "type": "unknown",
        "entity": "unknown",
    }
