from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx


JSONDict = Dict[str, Any]


def _node_id(node_type: str, *parts: str) -> str:
    return f"{node_type}:{'|'.join(parts)}"


def _get_node_data(graph: nx.DiGraph, node_id: str) -> JSONDict:
    node = graph.nodes.get(node_id, {})
    data = node.get("data")
    if isinstance(data, dict):
        return data
    return {}


def _safe_successors_by_relation(graph: nx.DiGraph, node_id: str, relation: str) -> List[str]:
    if not graph.has_node(node_id):
        return []
    out: List[str] = []
    for _, dst, attrs in graph.out_edges(node_id, data=True):
        if attrs.get("relation") == relation:
            out.append(dst)
    return out


def _safe_predecessors_by_relation(graph: nx.DiGraph, node_id: str, relation: str) -> List[str]:
    if not graph.has_node(node_id):
        return []
    out: List[str] = []
    for src, _, attrs in graph.in_edges(node_id, data=True):
        if attrs.get("relation") == relation:
            out.append(src)
    return out


def _extract_key_part(node_id: str, index: int = 0) -> Optional[str]:
    if ":" not in node_id:
        return None
    _, raw = node_id.split(":", 1)
    parts = raw.split("|")
    if index >= len(parts):
        return None
    return parts[index]


def _invoice_for_invoice_item(graph: nx.DiGraph, invoice_item_node: str) -> Optional[str]:
    billing_document = _extract_key_part(invoice_item_node, 0)
    if not billing_document:
        return None
    invoice_node = _node_id("Invoice", billing_document)
    if graph.has_node(invoice_node):
        return invoice_node
    return None


def _order_item_nodes_for_order(graph: nx.DiGraph, order_node: str) -> List[str]:
    return _safe_successors_by_relation(graph, order_node, "HAS_ITEM")


def _delivery_item_nodes_for_order_item(graph: nx.DiGraph, order_item_node: str) -> List[str]:
    return _safe_successors_by_relation(graph, order_item_node, "DELIVERED_IN")


def _invoice_item_nodes_for_delivery_item(graph: nx.DiGraph, delivery_item_node: str) -> List[str]:
    return _safe_successors_by_relation(graph, delivery_item_node, "BILLED_IN")


def _json_result(ok: bool, message: str, payload: Optional[JSONDict] = None) -> JSONDict:
    return {
        "ok": ok,
        "message": message,
        "data": payload or {},
    }


def find_journal_by_invoice(graph: nx.DiGraph, invoice_id: str) -> JSONDict:
    """Traverse Invoice -> JournalEntry via POSTED_AS."""
    invoice_node = _node_id("Invoice", str(invoice_id))
    if not graph.has_node(invoice_node):
        return _json_result(False, "Invoice not found", {"invoice_id": invoice_id, "journal_entries": []})

    journal_nodes = _safe_successors_by_relation(graph, invoice_node, "POSTED_AS")
    journals: List[JSONDict] = []
    for node_id in journal_nodes:
        journals.append(
            {
                "node_id": node_id,
                "accountingDocument": _extract_key_part(node_id, 0),
                "attributes": _get_node_data(graph, node_id),
            }
        )

    return _json_result(
        True,
        "Journal entries retrieved",
        {
            "invoice_id": invoice_id,
            "invoice_node": invoice_node,
            "journal_count": len(journals),
            "journal_entries": journals,
        },
    )


def trace_order_flow(graph: nx.DiGraph, order_id: str) -> JSONDict:
    """Trace Order -> Delivery -> Invoice -> Journal -> Payment using edge traversal.

    Traversal path in this graph model:
    Order -HAS_ITEM-> OrderItem -DELIVERED_IN-> DeliveryItem -BILLED_IN-> InvoiceItem
    InvoiceItem is mapped to Invoice by invoice key prefix in composite node ID.
    Invoice -POSTED_AS-> JournalEntry
    Invoice -PAID_BY-> Payment
    """
    order_node = _node_id("Order", str(order_id))
    if not graph.has_node(order_node):
        return _json_result(False, "Order not found", {"order_id": order_id})

    order_item_nodes = _order_item_nodes_for_order(graph, order_node)

    delivery_item_nodes: Set[str] = set()
    for oi in order_item_nodes:
        delivery_item_nodes.update(_delivery_item_nodes_for_order_item(graph, oi))

    delivery_nodes: Set[str] = set()
    for di in delivery_item_nodes:
        delivery_id = _extract_key_part(di, 0)
        if delivery_id:
            dn = _node_id("Delivery", delivery_id)
            if graph.has_node(dn):
                delivery_nodes.add(dn)

    invoice_item_nodes: Set[str] = set()
    for di in delivery_item_nodes:
        invoice_item_nodes.update(_invoice_item_nodes_for_delivery_item(graph, di))

    invoice_nodes: Set[str] = set()
    for ii in invoice_item_nodes:
        inv = _invoice_for_invoice_item(graph, ii)
        if inv:
            invoice_nodes.add(inv)

    journal_nodes: Set[str] = set()
    payment_nodes: Set[str] = set()
    for inv in invoice_nodes:
        journal_nodes.update(_safe_successors_by_relation(graph, inv, "POSTED_AS"))
        payment_nodes.update(_safe_successors_by_relation(graph, inv, "PAID_BY"))

    return _json_result(
        True,
        "Order flow traced",
        {
            "order_id": order_id,
            "order_node": order_node,
            "order_item_count": len(order_item_nodes),
            "delivery_count": len(delivery_nodes),
            "invoice_count": len(invoice_nodes),
            "journal_count": len(journal_nodes),
            "payment_count": len(payment_nodes),
            "order_items": sorted(order_item_nodes),
            "deliveries": sorted(delivery_nodes),
            "delivery_items": sorted(delivery_item_nodes),
            "invoices": sorted(invoice_nodes),
            "invoice_items": sorted(invoice_item_nodes),
            "journals": sorted(journal_nodes),
            "payments": sorted(payment_nodes),
        },
    )


def find_orders_without_invoice(graph: nx.DiGraph) -> JSONDict:
    """Find orders that have delivery but no invoice."""
    order_nodes = [n for n, attrs in graph.nodes(data=True) if attrs.get("node_type") == "Order"]

    results: List[JSONDict] = []
    for order_node in order_nodes:
        order_id = _extract_key_part(order_node, 0)
        order_item_nodes = _order_item_nodes_for_order(graph, order_node)

        delivery_item_nodes: Set[str] = set()
        for oi in order_item_nodes:
            delivery_item_nodes.update(_delivery_item_nodes_for_order_item(graph, oi))

        has_delivery = len(delivery_item_nodes) > 0
        has_invoice = False

        if has_delivery:
            for di in delivery_item_nodes:
                if _invoice_item_nodes_for_delivery_item(graph, di):
                    has_invoice = True
                    break

        if has_delivery and not has_invoice:
            delivery_ids = sorted(
                {
                    _extract_key_part(di, 0)
                    for di in delivery_item_nodes
                    if _extract_key_part(di, 0) is not None
                }
            )
            results.append(
                {
                    "order_id": order_id,
                    "order_node": order_node,
                    "delivery_ids": delivery_ids,
                    "delivery_item_count": len(delivery_item_nodes),
                }
            )

    return _json_result(
        True,
        "Orders with delivery but no invoice retrieved",
        {
            "count": len(results),
            "orders": sorted(results, key=lambda x: x.get("order_id") or ""),
        },
    )


def top_products_by_billing(graph: nx.DiGraph, limit: int = 10) -> JSONDict:
    """Count product frequency in invoiced items.

    Traversal:
    InvoiceItem <-BILLED_IN- DeliveryItem <-DELIVERED_IN- OrderItem -OF_PRODUCT-> Product
    """
    invoice_item_nodes = [n for n, attrs in graph.nodes(data=True) if attrs.get("node_type") == "InvoiceItem"]

    product_counter: Counter[str] = Counter()
    unresolved_invoice_items = 0

    for invoice_item in invoice_item_nodes:
        delivery_items = _safe_predecessors_by_relation(graph, invoice_item, "BILLED_IN")

        products_for_line: Set[str] = set()
        for delivery_item in delivery_items:
            order_items = _safe_predecessors_by_relation(graph, delivery_item, "DELIVERED_IN")
            for order_item in order_items:
                product_nodes = _safe_successors_by_relation(graph, order_item, "OF_PRODUCT")
                for product_node in product_nodes:
                    product_id = _extract_key_part(product_node, 0)
                    if product_id:
                        products_for_line.add(product_id)

        if not products_for_line:
            unresolved_invoice_items += 1
            continue

        for product_id in products_for_line:
            product_counter[product_id] += 1

    ranked = product_counter.most_common(max(limit, 0))
    top_products = [
        {
            "product_id": product_id,
            "invoice_line_count": count,
            "product_node": _node_id("Product", product_id),
            "product_attributes": _get_node_data(graph, _node_id("Product", product_id)),
        }
        for product_id, count in ranked
    ]

    return _json_result(
        True,
        "Top products by billed frequency retrieved",
        {
            "limit": limit,
            "invoice_item_count": len(invoice_item_nodes),
            "resolved_invoice_item_count": len(invoice_item_nodes) - unresolved_invoice_items,
            "unresolved_invoice_item_count": unresolved_invoice_items,
            "top_products": top_products,
        },
    )


def execute_nl_query(graph: nx.DiGraph, query: str) -> JSONDict:
    """Lightweight NL router that maps text to query functions.

    Supported intents:
    - journal by invoice
    - trace order flow
    - orders without invoice
    - top products by billing
    """
    q = (query or "").strip().lower()
    if not q:
        return _json_result(False, "Empty query")

    if "journal" in q and "invoice" in q:
        token = _extract_last_number_like_token(query)
        if token is None:
            return _json_result(False, "Invoice ID not found in query")
        return find_journal_by_invoice(graph, token)

    if "trace" in q and "order" in q:
        token = _extract_last_number_like_token(query)
        if token is None:
            return _json_result(False, "Order ID not found in query")
        return trace_order_flow(graph, token)

    if "without invoice" in q or ("no invoice" in q and "order" in q):
        return find_orders_without_invoice(graph)

    if "top" in q and "product" in q and ("billing" in q or "invoice" in q):
        limit = _extract_limit(query) or 10
        return top_products_by_billing(graph, limit=limit)

    return _json_result(False, "Unsupported query intent")


def _extract_last_number_like_token(text: str) -> Optional[str]:
    tokens = text.replace(",", " ").split()
    candidates = [t for t in tokens if any(ch.isdigit() for ch in t)]
    if not candidates:
        return None
    token = candidates[-1]
    keep = "".join(ch for ch in token if ch.isalnum())
    return keep or None


def _extract_limit(text: str) -> Optional[int]:
    tokens = text.replace(",", " ").split()
    ints: List[int] = []
    for t in tokens:
        raw = "".join(ch for ch in t if ch.isdigit())
        if raw:
            try:
                ints.append(int(raw))
            except ValueError:
                continue
    if not ints:
        return None
    return ints[-1]
