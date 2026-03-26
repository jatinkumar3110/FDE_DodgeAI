from __future__ import annotations

from typing import Any, Dict


JSONDict = Dict[str, Any]


def plan_query(parsed_query: JSONDict) -> JSONDict:
    """Translate parsed intent into a deterministic structured query plan."""
    intent = (parsed_query or {}).get("intent")

    if intent == "find_journal":
        return {
            "type": "traversal",
            "entity": "Invoice",
            "start": "Invoice",
            "end": "JournalEntry",
            "path": ["Invoice", "JournalEntry"],
            "relation": "POSTED_AS",
        }

    if intent == "trace_order":
        return {
            "type": "traversal",
            "entity": "Order",
            "start": "Order",
            "end": "Payment",
            "path": ["Order", "Delivery", "Invoice", "JournalEntry", "Payment"],
            "mode": "order_to_cash",
        }

    if intent == "orders_without_invoice":
        return {
            "type": "anomaly_detection",
            "entity": "Order",
            "condition": "has_delivery_and_no_invoice",
            "severity": "high",
        }

    if intent == "top_products":
        return {
            "type": "aggregation",
            "entity": "InvoiceItem",
            "group_by": "product_id",
            "metric": "count",
            "limit": parsed_query.get("limit", 5),
            "sort": "desc",
        }

    if intent == "trace_billing":
        return {
            "type": "traversal",
            "entity": "Invoice",
            "start": "Invoice",
            "end": "Order",
            "path": ["Invoice", "Delivery", "Order", "JournalEntry", "Payment"],
            "mode": "billing_to_order",
        }

    if intent == "broken_flows":
        return {
            "type": "anomaly_detection",
            "entity": "DeliveryItem|InvoiceItem",
            "condition": parsed_query.get("type", "unknown"),
            "severity": "medium",
        }

    return {
        "type": "unknown",
        "entity": "unknown",
    }
