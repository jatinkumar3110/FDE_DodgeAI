from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set

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


def _dedupe_preserve(items: Sequence[str]) -> List[str]:
    seen: Set[str] = set()
    output: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _node_visual_metadata(graph: nx.DiGraph, node_id: str) -> JSONDict:
    attrs = graph.nodes.get(node_id, {})
    return {
        "id": node_id,
        "type": attrs.get("node_type", "Unknown"),
        "label": attrs.get("key") or node_id,
        "source_entity": attrs.get("source_entity"),
    }


def _graph_path_payload(graph: nx.DiGraph, nodes: Sequence[str], edge_limit: int = 500) -> JSONDict:
    node_set = set(nodes)
    edges: List[JSONDict] = []
    for source, target, attrs in graph.edges(data=True):
        if source in node_set and target in node_set:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": attrs.get("relation"),
                }
            )
            if len(edges) >= edge_limit:
                break

    return {
        "nodes": list(nodes),
        "edges": edges,
    }


def _attach_visuals(graph: nx.DiGraph, payload: JSONDict, highlight_nodes: Sequence[str]) -> JSONDict:
    filtered_nodes = [node for node in _dedupe_preserve(highlight_nodes) if graph.has_node(node)]
    payload["highlight_nodes"] = filtered_nodes
    payload["highlight_node_count"] = len(filtered_nodes)
    payload["highlight_node_metadata"] = [_node_visual_metadata(graph, node) for node in filtered_nodes[:60]]
    payload["graph_path"] = _graph_path_payload(graph, filtered_nodes)
    return payload


def _json_result(ok: bool, message: str, payload: Optional[JSONDict] = None) -> JSONDict:
    return {
        "ok": ok,
        "message": message,
        "data": payload or {},
    }


def find_journal_by_invoice(graph: nx.DiGraph, invoice_id: str) -> JSONDict:
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

    payload = {
        "invoice_id": str(invoice_id),
        "invoice_node": invoice_node,
        "journal_count": len(journals),
        "journal_entries": journals,
    }
    _attach_visuals(graph, payload, [invoice_node, *journal_nodes])
    return _json_result(True, "Journal entries retrieved", payload)


def trace_order_flow(graph: nx.DiGraph, order_id: str) -> JSONDict:
    order_node = _node_id("Order", str(order_id))
    if not graph.has_node(order_node):
        return _json_result(False, "Order not found", {"order_id": order_id})

    order_item_nodes = _order_item_nodes_for_order(graph, order_node)

    delivery_item_nodes: Set[str] = set()
    for order_item in order_item_nodes:
        delivery_item_nodes.update(_delivery_item_nodes_for_order_item(graph, order_item))

    delivery_nodes: Set[str] = set()
    for delivery_item in delivery_item_nodes:
        delivery_id = _extract_key_part(delivery_item, 0)
        if delivery_id:
            delivery_node = _node_id("Delivery", delivery_id)
            if graph.has_node(delivery_node):
                delivery_nodes.add(delivery_node)

    invoice_item_nodes: Set[str] = set()
    for delivery_item in delivery_item_nodes:
        invoice_item_nodes.update(_invoice_item_nodes_for_delivery_item(graph, delivery_item))

    invoice_nodes: Set[str] = set()
    for invoice_item in invoice_item_nodes:
        invoice_node = _invoice_for_invoice_item(graph, invoice_item)
        if invoice_node:
            invoice_nodes.add(invoice_node)

    journal_nodes: Set[str] = set()
    payment_nodes: Set[str] = set()
    for invoice_node in invoice_nodes:
        journal_nodes.update(_safe_successors_by_relation(graph, invoice_node, "POSTED_AS"))
        payment_nodes.update(_safe_successors_by_relation(graph, invoice_node, "PAID_BY"))

    highlight_nodes = [
        order_node,
        *sorted(order_item_nodes),
        *sorted(delivery_nodes),
        *sorted(delivery_item_nodes),
        *sorted(invoice_nodes),
        *sorted(invoice_item_nodes),
        *sorted(journal_nodes),
        *sorted(payment_nodes),
    ]

    payload = {
        "order_id": str(order_id),
        "order_node": order_node,
        "flow_path": "Order -> Delivery -> Invoice -> JournalEntry -> Payment",
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
    }
    _attach_visuals(graph, payload, highlight_nodes)
    return _json_result(True, "Order flow traced", payload)


def find_orders_without_invoice(graph: nx.DiGraph) -> JSONDict:
    order_nodes = [n for n, attrs in graph.nodes(data=True) if attrs.get("node_type") == "Order"]

    results: List[JSONDict] = []
    highlight_nodes: List[str] = []

    for order_node in order_nodes:
        order_id = _extract_key_part(order_node, 0)
        order_item_nodes = _order_item_nodes_for_order(graph, order_node)

        delivery_item_nodes: Set[str] = set()
        for order_item in order_item_nodes:
            delivery_item_nodes.update(_delivery_item_nodes_for_order_item(graph, order_item))

        has_delivery = len(delivery_item_nodes) > 0
        has_invoice = False

        if has_delivery:
            for delivery_item in delivery_item_nodes:
                if _invoice_item_nodes_for_delivery_item(graph, delivery_item):
                    has_invoice = True
                    break

        if has_delivery and not has_invoice:
            delivery_ids = sorted(
                {
                    _extract_key_part(delivery_item, 0)
                    for delivery_item in delivery_item_nodes
                    if _extract_key_part(delivery_item, 0) is not None
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
            highlight_nodes.append(order_node)
            highlight_nodes.extend(sorted(delivery_item_nodes))

    payload = {
        "count": len(results),
        "orders": sorted(results, key=lambda row: row.get("order_id") or ""),
    }
    _attach_visuals(graph, payload, highlight_nodes[:300])
    return _json_result(True, "Orders with delivery but no invoice retrieved", payload)


def top_products_by_billing(graph: nx.DiGraph, limit: int = 5) -> JSONDict:
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
    top_products: List[JSONDict] = []
    highlight_nodes: List[str] = []
    for product_id, count in ranked:
        product_node = _node_id("Product", product_id)
        highlight_nodes.append(product_node)
        top_products.append(
            {
                "product_id": product_id,
                "invoice_line_count": count,
                "product_node": product_node,
                "product_attributes": _get_node_data(graph, product_node),
            }
        )

    payload = {
        "limit": limit,
        "invoice_item_count": len(invoice_item_nodes),
        "resolved_invoice_item_count": len(invoice_item_nodes) - unresolved_invoice_items,
        "unresolved_invoice_item_count": unresolved_invoice_items,
        "top_products": top_products,
    }
    _attach_visuals(graph, payload, highlight_nodes)
    return _json_result(True, "Top products by billed frequency retrieved", payload)


def trace_billing(graph: nx.DiGraph, invoice_id: str) -> JSONDict:
    invoice_node = _node_id("Invoice", str(invoice_id))
    if not graph.has_node(invoice_node):
        return _json_result(False, "Invoice not found", {"invoice_id": invoice_id})

    invoice_item_nodes = [
        node_id
        for node_id, attrs in graph.nodes(data=True)
        if attrs.get("node_type") == "InvoiceItem" and _extract_key_part(node_id, 0) == str(invoice_id)
    ]

    delivery_item_nodes: Set[str] = set()
    for invoice_item in invoice_item_nodes:
        delivery_item_nodes.update(_safe_predecessors_by_relation(graph, invoice_item, "BILLED_IN"))

    delivery_nodes: Set[str] = set()
    order_item_nodes: Set[str] = set()
    order_nodes: Set[str] = set()

    for delivery_item in delivery_item_nodes:
        delivery_id = _extract_key_part(delivery_item, 0)
        if delivery_id:
            delivery_node = _node_id("Delivery", delivery_id)
            if graph.has_node(delivery_node):
                delivery_nodes.add(delivery_node)

        upstream_order_items = _safe_predecessors_by_relation(graph, delivery_item, "DELIVERED_IN")
        order_item_nodes.update(upstream_order_items)
        for order_item in upstream_order_items:
            order_id = _extract_key_part(order_item, 0)
            if order_id:
                order_node = _node_id("Order", order_id)
                if graph.has_node(order_node):
                    order_nodes.add(order_node)

    journal_nodes = sorted(_safe_successors_by_relation(graph, invoice_node, "POSTED_AS"))
    payment_nodes = sorted(_safe_successors_by_relation(graph, invoice_node, "PAID_BY"))

    highlight_nodes = [
        invoice_node,
        *sorted(invoice_item_nodes),
        *sorted(delivery_nodes),
        *sorted(delivery_item_nodes),
        *sorted(order_nodes),
        *sorted(order_item_nodes),
        *journal_nodes,
        *payment_nodes,
    ]

    payload = {
        "invoice_id": str(invoice_id),
        "invoice_node": invoice_node,
        "flow_path": "Invoice -> Delivery -> Order and Invoice -> JournalEntry -> Payment",
        "invoice_item_count": len(invoice_item_nodes),
        "delivery_count": len(delivery_nodes),
        "order_count": len(order_nodes),
        "journal_count": len(journal_nodes),
        "payment_count": len(payment_nodes),
        "deliveries": sorted(delivery_nodes),
        "delivery_items": sorted(delivery_item_nodes),
        "orders": sorted(order_nodes),
        "order_items": sorted(order_item_nodes),
        "journals": journal_nodes,
        "payments": payment_nodes,
    }
    _attach_visuals(graph, payload, highlight_nodes)
    return _json_result(True, "Billing flow traced", payload)


def find_broken_flows(graph: nx.DiGraph, type: str) -> JSONDict:
    flow_type = (type or "").strip().lower()
    if flow_type not in {"delivered_not_billed", "billed_without_delivery"}:
        return _json_result(False, "Invalid broken flow type", {"type": flow_type})

    issues: List[JSONDict] = []
    highlight_nodes: List[str] = []

    if flow_type == "delivered_not_billed":
        delivery_item_nodes = [node_id for node_id, attrs in graph.nodes(data=True) if attrs.get("node_type") == "DeliveryItem"]
        for delivery_item in delivery_item_nodes:
            invoice_items = _safe_successors_by_relation(graph, delivery_item, "BILLED_IN")
            if invoice_items:
                continue
            issues.append(
                {
                    "delivery_item_node": delivery_item,
                    "delivery_id": _extract_key_part(delivery_item, 0),
                    "delivery_item_id": _extract_key_part(delivery_item, 1),
                }
            )
            highlight_nodes.append(delivery_item)

    if flow_type == "billed_without_delivery":
        invoice_item_nodes = [node_id for node_id, attrs in graph.nodes(data=True) if attrs.get("node_type") == "InvoiceItem"]
        for invoice_item in invoice_item_nodes:
            delivery_items = _safe_predecessors_by_relation(graph, invoice_item, "BILLED_IN")
            if delivery_items:
                continue
            issues.append(
                {
                    "invoice_item_node": invoice_item,
                    "invoice_id": _extract_key_part(invoice_item, 0),
                    "invoice_item_id": _extract_key_part(invoice_item, 1),
                }
            )
            highlight_nodes.append(invoice_item)

    payload = {
        "type": flow_type,
        "count": len(issues),
        "issues": issues,
    }
    _attach_visuals(graph, payload, highlight_nodes[:300])
    return _json_result(True, "Broken flow analysis complete", payload)


def execute_nl_query(graph: nx.DiGraph, query: str) -> JSONDict:
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

    if "trace" in q and "billing" in q:
        token = _extract_last_number_like_token(query)
        if token is None:
            return _json_result(False, "Invoice ID not found in query")
        return trace_billing(graph, token)

    if "broken" in q and "flow" in q:
        if "delivered" in q and "billed" in q and "not" in q:
            return find_broken_flows(graph, "delivered_not_billed")
        if "billed" in q and "without delivery" in q:
            return find_broken_flows(graph, "billed_without_delivery")
        return _json_result(False, "Broken flow type not recognized")

    if "without invoice" in q or ("no invoice" in q and "order" in q):
        return find_orders_without_invoice(graph)

    if "top" in q and "product" in q and ("billing" in q or "invoice" in q):
        limit = _extract_limit(query) or 10
        return top_products_by_billing(graph, limit=limit)

    return _json_result(False, "Unsupported query intent")


def _extract_last_number_like_token(text: str) -> Optional[str]:
    tokens = text.replace(",", " ").split()
    candidates = [token for token in tokens if any(ch.isdigit() for ch in token)]
    if not candidates:
        return None
    token = candidates[-1]
    keep = "".join(ch for ch in token if ch.isalnum())
    return keep or None


def _extract_limit(text: str) -> Optional[int]:
    tokens = text.replace(",", " ").split()
    ints: List[int] = []
    for token in tokens:
        raw = "".join(ch for ch in token if ch.isdigit())
        if raw:
            try:
                ints.append(int(raw))
            except ValueError:
                continue
    if not ints:
        return None
    return ints[-1]
