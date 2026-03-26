from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import networkx as nx

from data_loader import load_all_jsonl, normalize_item_number


JSONDict = Dict[str, Any]
Dataset = Mapping[str, Sequence[JSONDict]]


def _s(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _item(value: Any) -> Optional[str]:
    normalized = normalize_item_number(value)
    return _s(normalized)


def _node_id(node_type: str, *parts: Optional[str]) -> str:
    safe_parts = [p for p in parts if p is not None and p != ""]
    return f"{node_type}:{'|'.join(safe_parts)}"


def _add_node(
    graph: nx.DiGraph,
    node_id: str,
    node_type: str,
    key: str,
    source_entity: str,
    attributes: Mapping[str, Any],
) -> None:
    node_attrs = {
        "node_type": node_type,
        "key": key,
        "source_entity": source_entity,
        "data": dict(attributes),
    }
    if graph.has_node(node_id):
        graph.nodes[node_id].update(node_attrs)
    else:
        graph.add_node(node_id, **node_attrs)


def _add_edge_or_track_missing(
    graph: nx.DiGraph,
    src: Optional[str],
    dst: Optional[str],
    relation: str,
    missing_counter: MutableMapping[str, int],
) -> None:
    if not src or not dst:
        missing_counter[relation] += 1
        return
    if not graph.has_node(src) or not graph.has_node(dst):
        missing_counter[relation] += 1
        return
    graph.add_edge(src, dst, relation=relation)


def _rows(dataset: Dataset, entity: str) -> Sequence[JSONDict]:
    return dataset.get(entity, [])


def build_o2c_graph(dataset: Dataset) -> nx.DiGraph:
    """Build Order-to-Cash graph from loaded ERP datasets.

    Expected entity keys include:
    - sales_order_headers, sales_order_items
    - outbound_delivery_headers, outbound_delivery_items
    - billing_document_headers, billing_document_items
    - journal_entry_items_accounts_receivable
    - payments_accounts_receivable
    - business_partners, products, plants
    """
    graph = nx.DiGraph()
    missing_edges: Dict[str, int] = defaultdict(int)

    order_nodes: Dict[str, str] = {}
    order_item_nodes: Dict[Tuple[str, str], str] = {}
    delivery_nodes: Dict[str, str] = {}
    delivery_item_nodes: Dict[Tuple[str, str], str] = {}
    invoice_nodes: Dict[str, str] = {}
    invoice_item_nodes: Dict[Tuple[str, str], str] = {}
    journal_nodes: Dict[str, str] = {}
    payment_nodes: Dict[str, str] = {}
    customer_nodes: Dict[str, str] = {}
    product_nodes: Dict[str, str] = {}
    plant_nodes: Dict[str, str] = {}

    for row in _rows(dataset, "sales_order_headers"):
        sales_order = _s(row.get("salesOrder"))
        if not sales_order:
            continue
        node = _node_id("Order", sales_order)
        _add_node(graph, node, "Order", sales_order, "sales_order_headers", row)
        order_nodes[sales_order] = node

    for row in _rows(dataset, "sales_order_items"):
        sales_order = _s(row.get("salesOrder"))
        sales_order_item = _item(row.get("salesOrderItem"))
        if not sales_order or not sales_order_item:
            continue
        key = f"{sales_order}|{sales_order_item}"
        node = _node_id("OrderItem", sales_order, sales_order_item)
        _add_node(graph, node, "OrderItem", key, "sales_order_items", row)
        order_item_nodes[(sales_order, sales_order_item)] = node

    for row in _rows(dataset, "outbound_delivery_headers"):
        delivery_document = _s(row.get("deliveryDocument"))
        if not delivery_document:
            continue
        node = _node_id("Delivery", delivery_document)
        _add_node(graph, node, "Delivery", delivery_document, "outbound_delivery_headers", row)
        delivery_nodes[delivery_document] = node

    for row in _rows(dataset, "outbound_delivery_items"):
        delivery_document = _s(row.get("deliveryDocument"))
        delivery_item = _item(row.get("deliveryDocumentItem"))
        if not delivery_document or not delivery_item:
            continue
        key = f"{delivery_document}|{delivery_item}"
        node = _node_id("DeliveryItem", delivery_document, delivery_item)
        _add_node(graph, node, "DeliveryItem", key, "outbound_delivery_items", row)
        delivery_item_nodes[(delivery_document, delivery_item)] = node

    for row in _rows(dataset, "billing_document_headers"):
        billing_document = _s(row.get("billingDocument"))
        if not billing_document:
            continue
        node = _node_id("Invoice", billing_document)
        _add_node(graph, node, "Invoice", billing_document, "billing_document_headers", row)
        invoice_nodes[billing_document] = node

    for row in _rows(dataset, "billing_document_items"):
        billing_document = _s(row.get("billingDocument"))
        billing_item = _item(row.get("billingDocumentItem"))
        if not billing_document or not billing_item:
            continue
        key = f"{billing_document}|{billing_item}"
        node = _node_id("InvoiceItem", billing_document, billing_item)
        _add_node(graph, node, "InvoiceItem", key, "billing_document_items", row)
        invoice_item_nodes[(billing_document, billing_item)] = node

    for row in _rows(dataset, "journal_entry_items_accounts_receivable"):
        accounting_document = _s(row.get("accountingDocument"))
        if not accounting_document:
            continue
        node = _node_id("JournalEntry", accounting_document)
        _add_node(
            graph,
            node,
            "JournalEntry",
            accounting_document,
            "journal_entry_items_accounts_receivable",
            row,
        )
        journal_nodes[accounting_document] = node

    for row in _rows(dataset, "payments_accounts_receivable"):
        accounting_document = _s(row.get("accountingDocument"))
        if not accounting_document:
            continue
        node = _node_id("Payment", accounting_document)
        _add_node(graph, node, "Payment", accounting_document, "payments_accounts_receivable", row)
        payment_nodes[accounting_document] = node

    for row in _rows(dataset, "business_partners"):
        business_partner = _s(row.get("businessPartner"))
        if not business_partner:
            continue
        node = _node_id("Customer", business_partner)
        _add_node(graph, node, "Customer", business_partner, "business_partners", row)
        customer_nodes[business_partner] = node

    for row in _rows(dataset, "products"):
        product = _s(row.get("product"))
        if not product:
            continue
        node = _node_id("Product", product)
        _add_node(graph, node, "Product", product, "products", row)
        product_nodes[product] = node

    for row in _rows(dataset, "plants"):
        plant = _s(row.get("plant"))
        if not plant:
            continue
        node = _node_id("Plant", plant)
        _add_node(graph, node, "Plant", plant, "plants", row)
        plant_nodes[plant] = node

    # Order -> OrderItem (HAS_ITEM)
    for (sales_order, sales_order_item), order_item_node in order_item_nodes.items():
        order_node = order_nodes.get(sales_order)
        _add_edge_or_track_missing(graph, order_node, order_item_node, "HAS_ITEM", missing_edges)

    # OrderItem -> DeliveryItem (DELIVERED_IN)
    for row in _rows(dataset, "outbound_delivery_items"):
        sales_order = _s(row.get("referenceSdDocument"))
        sales_order_item = _item(row.get("referenceSdDocumentItem"))
        delivery_document = _s(row.get("deliveryDocument"))
        delivery_item = _item(row.get("deliveryDocumentItem"))

        src = order_item_nodes.get((sales_order, sales_order_item)) if sales_order and sales_order_item else None
        dst = delivery_item_nodes.get((delivery_document, delivery_item)) if delivery_document and delivery_item else None
        _add_edge_or_track_missing(graph, src, dst, "DELIVERED_IN", missing_edges)

    # DeliveryItem -> InvoiceItem (BILLED_IN)
    for row in _rows(dataset, "billing_document_items"):
        delivery_document = _s(row.get("referenceSdDocument"))
        delivery_item = _item(row.get("referenceSdDocumentItem"))
        billing_document = _s(row.get("billingDocument"))
        billing_item = _item(row.get("billingDocumentItem"))

        src = delivery_item_nodes.get((delivery_document, delivery_item)) if delivery_document and delivery_item else None
        dst = invoice_item_nodes.get((billing_document, billing_item)) if billing_document and billing_item else None
        _add_edge_or_track_missing(graph, src, dst, "BILLED_IN", missing_edges)

    # Invoice -> JournalEntry (POSTED_AS), Invoice -> Payment (PAID_BY)
    for row in _rows(dataset, "billing_document_headers"):
        billing_document = _s(row.get("billingDocument"))
        accounting_document = _s(row.get("accountingDocument"))
        invoice_node = invoice_nodes.get(billing_document) if billing_document else None

        journal_node = journal_nodes.get(accounting_document) if accounting_document else None
        payment_node = payment_nodes.get(accounting_document) if accounting_document else None

        _add_edge_or_track_missing(graph, invoice_node, journal_node, "POSTED_AS", missing_edges)
        _add_edge_or_track_missing(graph, invoice_node, payment_node, "PAID_BY", missing_edges)

    # Order -> Customer (ORDERED_BY)
    for row in _rows(dataset, "sales_order_headers"):
        sales_order = _s(row.get("salesOrder"))
        sold_to_party = _s(row.get("soldToParty"))
        src = order_nodes.get(sales_order) if sales_order else None
        dst = customer_nodes.get(sold_to_party) if sold_to_party else None
        _add_edge_or_track_missing(graph, src, dst, "ORDERED_BY", missing_edges)

    # OrderItem -> Product (OF_PRODUCT)
    for row in _rows(dataset, "sales_order_items"):
        sales_order = _s(row.get("salesOrder"))
        sales_order_item = _item(row.get("salesOrderItem"))
        material = _s(row.get("material"))

        src = order_item_nodes.get((sales_order, sales_order_item)) if sales_order and sales_order_item else None
        dst = product_nodes.get(material) if material else None
        _add_edge_or_track_missing(graph, src, dst, "OF_PRODUCT", missing_edges)

    # DeliveryItem -> Plant (FROM_PLANT)
    for row in _rows(dataset, "outbound_delivery_items"):
        delivery_document = _s(row.get("deliveryDocument"))
        delivery_item = _item(row.get("deliveryDocumentItem"))
        plant = _s(row.get("plant"))

        src = delivery_item_nodes.get((delivery_document, delivery_item)) if delivery_document and delivery_item else None
        dst = plant_nodes.get(plant) if plant else None
        _add_edge_or_track_missing(graph, src, dst, "FROM_PLANT", missing_edges)

    graph.graph["missing_relationships"] = dict(missing_edges)
    graph.graph["node_count"] = graph.number_of_nodes()
    graph.graph["edge_count"] = graph.number_of_edges()

    return graph


def build_o2c_graph_from_path(root_dir: str | Path) -> nx.DiGraph:
    """Convenience wrapper: load JSONL data recursively and build the graph."""
    dataset = load_all_jsonl(root_dir)
    return build_o2c_graph(dataset)
