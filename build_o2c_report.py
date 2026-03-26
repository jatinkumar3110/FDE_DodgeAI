import json
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("sap-order-to-cash-dataset") / "sap-o2c-data"
PROFILE_PATH = Path("analysis_output") / "dataset_profile.json"
REPORT_PATH = Path("analysis_output") / "dataset_analysis_report.md"


def read_jsonl(entity):
    entity_dir = ROOT / entity
    rows = []
    for fp in sorted(entity_dir.glob("*.jsonl")):
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    return rows


def idx(rows, key):
    m = defaultdict(list)
    for r in rows:
        v = r.get(key)
        if v is not None:
            m[str(v)].append(r)
    return m


def first_non_empty(*vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def fmt(v):
    if v is None:
        return "null"
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return str(v)


def choose_pk(meta):
    pks = meta.get("pk_candidates", [])
    if pks:
        preferred = [
            x for x in pks
            if any(k in x.lower() for k in ["id", "number", "document", "order", "delivery", "billing", "partner", "product", "plant", "entry"]) 
        ]
        return preferred[0] if preferred else pks[0]
    comp = meta.get("composite_pk_candidates", [])
    if comp:
        return " + ".join(comp[0])
    return None


def main():
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    entities = profile["entities"]
    relationships = profile["relationships"]

    # Build FK suggestions per entity from relationship evidence
    fk_by_entity = defaultdict(list)
    for r in relationships:
        if r["coverage_source"] >= 0.5:
            fk_by_entity[r["source_entity"]].append(r)

    # Load key process datasets for flow and edge-case analysis
    soh = read_jsonl("sales_order_headers")
    soi = read_jsonl("sales_order_items")
    odh = read_jsonl("outbound_delivery_headers")
    odi = read_jsonl("outbound_delivery_items")
    bdh = read_jsonl("billing_document_headers")
    bdi = read_jsonl("billing_document_items")
    par = read_jsonl("payments_accounts_receivable")
    jei = read_jsonl("journal_entry_items_accounts_receivable")

    soh_by_order = idx(soh, "salesOrder")
    soi_by_order = idx(soi, "salesOrder")
    odi_by_order = idx(odi, "referenceSdDocument")
    odi_by_delivery = idx(odi, "deliveryDocument")
    odh_by_delivery = idx(odh, "deliveryDocument")
    bdi_by_delivery = idx(bdi, "referenceSdDocument")
    bdh_by_billing = idx(bdh, "billingDocument")
    par_by_accounting = idx(par, "accountingDocument")
    jei_by_accounting = idx(jei, "accountingDocument")
    jei_by_refdoc = idx(jei, "referenceDocument")

    # Edge-case metrics
    order_ids = set(soh_by_order.keys())
    orders_with_items = set(soi_by_order.keys())
    orders_with_delivery = set(odi_by_order.keys())

    delivery_ids = set(odh_by_delivery.keys())
    deliveries_with_items = set(odi_by_delivery.keys())
    deliveries_with_billing = set(bdi_by_delivery.keys())

    billing_ids = set(bdh_by_billing.keys())
    billings_with_items = set(idx(bdi, "billingDocument").keys())

    accounting_docs = set(str(r.get("accountingDocument")) for r in bdh if r.get("accountingDocument") is not None)
    accounting_with_payment = set(par_by_accounting.keys())
    accounting_with_journal = set(jei_by_accounting.keys())

    missing = {
        "orders_without_items": len(order_ids - orders_with_items),
        "orders_without_delivery": len(order_ids - orders_with_delivery),
        "deliveries_without_items": len(delivery_ids - deliveries_with_items),
        "deliveries_without_billing": len(delivery_ids - deliveries_with_billing),
        "billing_without_items": len(billing_ids - billings_with_items),
        "billing_without_payment_by_accounting": len(accounting_docs - accounting_with_payment),
        "billing_without_journal_by_accounting": len(accounting_docs - accounting_with_journal),
    }

    # Find orphan references for high-confidence links
    orphans = {}
    # outbound_delivery_items.referenceSdDocument -> sales_order_headers.salesOrder
    orphans["delivery_item_order_ref_orphans"] = len([k for k in odi_by_order if k not in order_ids])
    # billing_document_items.referenceSdDocument -> outbound_delivery_headers.deliveryDocument
    orphans["billing_item_delivery_ref_orphans"] = len([k for k in bdi_by_delivery if k not in delivery_ids])
    # journal.referenceDocument -> billing_document_headers.billingDocument
    orphans["journal_reference_billing_orphans"] = len([k for k in jei_by_refdoc if k not in billing_ids])

    # Nullable hot spots
    nullable = []
    for e, meta in entities.items():
        for f, finfo in meta["fields"].items():
            nr = finfo["null_ratio"]
            if nr > 0.2:
                nullable.append((e, f, nr))
    nullable.sort(key=lambda x: (-x[2], x[0], x[1]))

    # Sample end-to-end flows
    flows = []
    for order_id in sorted(order_ids):
        del_items = odi_by_order.get(order_id, [])
        if not del_items:
            continue
        delivery_ids_for_order = sorted({str(x.get("deliveryDocument")) for x in del_items if x.get("deliveryDocument") is not None})
        billing_ids_for_order = set()
        accounting_docs_for_order = set()
        payments_for_order = []
        journals_for_order = []

        for did in delivery_ids_for_order:
            for bi in bdi_by_delivery.get(did, []):
                bd = bi.get("billingDocument")
                if bd is None:
                    continue
                bd = str(bd)
                billing_ids_for_order.add(bd)
                for bh in bdh_by_billing.get(bd, []):
                    ad = bh.get("accountingDocument")
                    if ad is not None:
                        ad = str(ad)
                        accounting_docs_for_order.add(ad)
                        payments_for_order.extend(par_by_accounting.get(ad, []))
                        journals_for_order.extend(jei_by_accounting.get(ad, []))
                journals_for_order.extend(jei_by_refdoc.get(bd, []))

        if billing_ids_for_order and (payments_for_order or journals_for_order):
            so = soh_by_order.get(order_id, [{}])[0]
            flows.append({
                "salesOrder": order_id,
                "soldToParty": so.get("soldToParty"),
                "salesOrg": so.get("salesOrganization"),
                "deliveries": delivery_ids_for_order,
                "billings": sorted(billing_ids_for_order),
                "accountingDocuments": sorted(accounting_docs_for_order),
                "payments": sorted({str(p.get("accountingDocument")) for p in payments_for_order if p.get("accountingDocument") is not None}),
                "journalReferences": sorted({str(j.get("accountingDocument")) for j in journals_for_order if j.get("accountingDocument") is not None}),
                "itemCount": len(soi_by_order.get(order_id, [])),
            })
        if len(flows) >= 3:
            break

    lines = []
    lines.append("# Dataset Analysis Report")
    lines.append("")

    lines.append("## Entities")
    lines.append("")

    for entity in sorted(entities.keys()):
        meta = entities[entity]
        pk = choose_pk(meta)
        lines.append(f"### Entity: {entity}")
        lines.append(f"- Records: {meta['row_count']}")
        lines.append(f"- Likely primary key: {pk if pk else 'not found (likely composite or no strict PK)'}")

        # Fields
        lines.append("- Fields:")
        for fname, finfo in sorted(meta["fields"].items()):
            dtype = finfo["type"]
            null_ratio = finfo["null_ratio"]
            marker = ""
            if pk and " + " not in pk and fname == pk:
                marker = " [primary key]"
            lines.append(f"  - {fname}: {dtype}; null_ratio={null_ratio:.2%}{marker}")

        # FK hints
        fk_hints = fk_by_entity.get(entity, [])
        if fk_hints:
            lines.append("- Possible foreign keys:")
            used = set()
            for r in sorted(fk_hints, key=lambda x: (-x["coverage_source"], x["source_field"])):
                key = (r["source_field"], r["target_entity"], r["target_field"])
                if key in used:
                    continue
                used.add(key)
                lines.append(
                    f"  - {r['source_field']} -> {r['target_entity']}.{r['target_field']} (source coverage={r['coverage_source']:.1%}, overlap={r['overlap_values']})"
                )
        lines.append("")

    lines.append("## Relationships")
    lines.append("")
    rel_priority = []
    for r in relationships:
        # Focus on meaningful process and master-data relationships
        if r["coverage_source"] < 0.5:
            continue
        rel_priority.append(r)

    # dedupe same source field to best target coverage for readability
    best = {}
    for r in rel_priority:
        k = (r["source_entity"], r["source_field"], r["target_entity"])
        best[k] = r

    for r in sorted(best.values(), key=lambda x: (x["source_entity"], x["source_field"], x["target_entity"])):
        cardinality = "(N) -> (1)"
        if r["estimated_cardinality"] == "1:1_or_N:1":
            cardinality = "(1 or N) -> (1)"
        lines.append(
            f"- {r['source_entity']} {cardinality} {r['target_entity']} via {r['source_field']} = {r['target_field']} (coverage={r['coverage_source']:.1%})"
        )
    lines.append("")

    lines.append("## Business Flow")
    lines.append("")
    lines.append("Sales Order -> Delivery -> Billing -> Payment -> Journal Entry")
    lines.append("")
    lines.append("- Sales Order to Delivery: outbound_delivery_items.referenceSdDocument links to sales_order_headers.salesOrder; delivery header is outbound_delivery_headers.deliveryDocument.")
    lines.append("- Delivery to Billing: billing_document_items.referenceSdDocument links to outbound_delivery_headers.deliveryDocument; billing header joins by billingDocument.")
    lines.append("- Billing to Payment: billing_document_headers.accountingDocument links to payments_accounts_receivable.accountingDocument.")
    lines.append("- Billing to Journal: journal_entry_items_accounts_receivable.referenceDocument links to billing_document_headers.billingDocument; accountingDocument also links to journals.")
    lines.append("")

    lines.append("## Edge Cases")
    lines.append("")
    lines.append("- Missing links (counts):")
    for k, v in missing.items():
        lines.append(f"  - {k}: {v}")
    lines.append("- Orphan reference checks:")
    for k, v in orphans.items():
        lines.append(f"  - {k}: {v}")
    lines.append("- Potential N:N bridge entities:")
    lines.append("  - product_plants bridges products and plants (many products per plant and many plants per product).")
    lines.append("  - product_storage_locations bridges products, plants, and storage locations.")
    lines.append("- Nullable fields (>20% null):")
    for e, f, nr in nullable[:25]:
        lines.append(f"  - {e}.{f}: {nr:.1%} null")
    lines.append("")

    lines.append("## Sample Insights")
    lines.append("")
    lines.append("### Record Counts by Entity")
    for entity in sorted(entities.keys()):
        lines.append(f"- {entity}: {entities[entity]['row_count']}")
    lines.append("")

    lines.append("### Sample End-to-End Flows")
    if not flows:
        lines.append("- No complete flow found from order to payment/journal in current sample.")
    else:
        for i, fl in enumerate(flows, start=1):
            lines.append(f"- Flow {i}: salesOrder={fl['salesOrder']}, soldToParty={fmt(fl['soldToParty'])}, salesOrg={fmt(fl['salesOrg'])}")
            lines.append(f"  - order_items={fl['itemCount']}")
            lines.append(f"  - deliveries={', '.join(fl['deliveries']) if fl['deliveries'] else 'none'}")
            lines.append(f"  - billings={', '.join(fl['billings']) if fl['billings'] else 'none'}")
            lines.append(f"  - accountingDocuments={', '.join(fl['accountingDocuments']) if fl['accountingDocuments'] else 'none'}")
            lines.append(f"  - payment_docs={', '.join(fl['payments']) if fl['payments'] else 'none'}")
            lines.append(f"  - journal_docs={', '.join(fl['journalReferences']) if fl['journalReferences'] else 'none'}")
    lines.append("")

    lines.append("### Noted Anomalies")
    anomaly_notes = []
    if missing["orders_without_delivery"] > 0:
        anomaly_notes.append("Some sales orders never progressed to delivery.")
    if missing["deliveries_without_billing"] > 0:
        anomaly_notes.append("Some deliveries are not billed.")
    if missing["billing_without_payment_by_accounting"] > 0:
        anomaly_notes.append("Some billing accounting documents have no corresponding payment records.")
    if missing["billing_without_journal_by_accounting"] > 0:
        anomaly_notes.append("Some billing accounting documents have no matching journal entries by accountingDocument.")
    if orphans["journal_reference_billing_orphans"] > 0:
        anomaly_notes.append("Some journal entries reference billing documents not present in billing headers.")
    if not anomaly_notes:
        anomaly_notes.append("No major anomalies detected in the core join paths.")
    for a in anomaly_notes:
        lines.append(f"- {a}")
    lines.append("")

    lines.append("## Suggested Graph Model")
    lines.append("")
    lines.append("### Node Types")
    lines.append("- Order (sales_order_headers)")
    lines.append("- OrderItem (sales_order_items)")
    lines.append("- Delivery (outbound_delivery_headers)")
    lines.append("- DeliveryItem (outbound_delivery_items)")
    lines.append("- Invoice (billing_document_headers)")
    lines.append("- InvoiceItem (billing_document_items)")
    lines.append("- Payment (payments_accounts_receivable)")
    lines.append("- JournalEntryAR (journal_entry_items_accounts_receivable)")
    lines.append("- Customer (business_partners)")
    lines.append("- CustomerAddress (business_partner_addresses)")
    lines.append("- Product (products)")
    lines.append("- Plant (plants)")
    lines.append("- ProductPlant (product_plants)")
    lines.append("- ProductStorageLocation (product_storage_locations)")
    lines.append("")

    lines.append("### Edge Types")
    lines.append("- Order -[HAS_ITEM]-> OrderItem via salesOrder")
    lines.append("- Order -[ORDERED_BY]-> Customer via soldToParty -> businessPartner")
    lines.append("- DeliveryItem -[DELIVERS_ORDER]-> Order via referenceSdDocument -> salesOrder")
    lines.append("- Delivery -[HAS_ITEM]-> DeliveryItem via deliveryDocument")
    lines.append("- InvoiceItem -[BILLS_DELIVERY]-> Delivery via referenceSdDocument -> deliveryDocument")
    lines.append("- Invoice -[HAS_ITEM]-> InvoiceItem via billingDocument")
    lines.append("- Invoice -[POSTED_TO]-> Payment via accountingDocument")
    lines.append("- Invoice -[POSTED_TO]-> JournalEntryAR via accountingDocument")
    lines.append("- JournalEntryAR -[REFERENCES_INVOICE]-> Invoice via referenceDocument -> billingDocument")
    lines.append("- OrderItem -[FOR_PRODUCT]-> Product via material -> product")
    lines.append("- DeliveryItem -[FROM_PLANT]-> Plant via plant")
    lines.append("- ProductPlant -[LINKS_PRODUCT]-> Product via product")
    lines.append("- ProductPlant -[LINKS_PLANT]-> Plant via plant")
    lines.append("- ProductStorageLocation -[STORES_PRODUCT]-> Product via product")
    lines.append("- ProductStorageLocation -[AT_PLANT]-> Plant via plant")
    lines.append("")

    lines.append("### Implementation Notes")
    lines.append("- Use stable business keys from source systems (e.g., salesOrder, deliveryDocument, billingDocument, accountingDocument) as node IDs.")
    lines.append("- Keep item entities as first-class nodes to preserve 1:N semantics and avoid property-array anti-patterns.")
    lines.append("- Persist relationship confidence/coverage metadata for inferred edges when strict FK constraints are absent.")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report: {REPORT_PATH.as_posix()}")


if __name__ == "__main__":
    main()
