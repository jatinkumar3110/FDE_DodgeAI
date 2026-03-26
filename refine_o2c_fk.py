import json
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path("sap-order-to-cash-dataset") / "sap-o2c-data"
OUT = Path("analysis_output")
OUT.mkdir(exist_ok=True)


ENTITIES = [
    "sales_order_headers",
    "sales_order_items",
    "sales_order_schedule_lines",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "billing_document_headers",
    "billing_document_items",
    "billing_document_cancellations",
    "payments_accounts_receivable",
    "journal_entry_items_accounts_receivable",
    "business_partners",
    "business_partner_addresses",
    "customer_company_assignments",
    "customer_sales_area_assignments",
    "products",
    "product_descriptions",
    "plants",
    "product_plants",
    "product_storage_locations",
]


def read_jsonl(entity):
    rows = []
    for fp in sorted((ROOT / entity).glob("*.jsonl")):
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


def key_stats(rows, cols):
    total = len(rows)
    complete = 0
    unique = set()
    dupes = 0
    for r in rows:
        parts = []
        ok = True
        for c in cols:
            v = r.get(c)
            if v is None:
                ok = False
                break
            parts.append(str(v))
        if not ok:
            continue
        complete += 1
        k = "|".join(parts)
        if k in unique:
            dupes += 1
        unique.add(k)
    unique_complete = (complete == len(unique))
    return {
        "total_rows": total,
        "complete_rows": complete,
        "unique_values": len(unique),
        "duplicate_complete_rows": dupes,
        "is_unique_on_complete_rows": unique_complete,
        "is_strict_key": unique_complete and complete == total,
    }


def build_index(rows, cols):
    idx = defaultdict(list)
    for r in rows:
        parts = []
        ok = True
        for c in cols:
            v = r.get(c)
            if v is None:
                ok = False
                break
            parts.append(str(v))
        if not ok:
            continue
        idx["|".join(parts)].append(r)
    return idx


def normalize_item(v):
    if v is None:
        return None
    s = str(v)
    # SAP item codes appear with and without left-zero padding across entities.
    s2 = s.lstrip("0")
    return s2 if s2 != "" else "0"


def build_index_with_normalizer(rows, cols, normalizers):
    idx = defaultdict(list)
    for r in rows:
        parts = []
        ok = True
        for c in cols:
            v = r.get(c)
            if v is None:
                ok = False
                break
            n = normalizers.get(c)
            if n is not None:
                v = n(v)
            parts.append(str(v))
        if not ok:
            continue
        idx["|".join(parts)].append(r)
    return idx


def validate_fk_with_normalizers(child_rows, child_cols, parent_rows, parent_cols, child_norm=None, parent_norm=None):
    child_norm = child_norm or {}
    parent_norm = parent_norm or {}
    c_idx = build_index_with_normalizer(child_rows, child_cols, child_norm)
    p_idx = build_index_with_normalizer(parent_rows, parent_cols, parent_norm)

    child_total = len(child_rows)
    child_complete = sum(len(v) for v in c_idx.values())
    child_null = child_total - child_complete

    matched_keys = set(c_idx.keys()) & set(p_idx.keys())
    orphan_keys = set(c_idx.keys()) - set(p_idx.keys())

    matched_child_rows = sum(len(c_idx[k]) for k in matched_keys)
    orphan_child_rows = sum(len(c_idx[k]) for k in orphan_keys)

    parent_keys_referenced = len(matched_keys)
    fanout = [len(c_idx[k]) for k in matched_keys]
    avg_children_per_parent = (sum(fanout) / len(fanout)) if fanout else 0.0
    max_children_per_parent = max(fanout) if fanout else 0

    return {
        "child_total_rows": child_total,
        "child_complete_fk_rows": child_complete,
        "child_null_fk_rows": child_null,
        "parent_distinct_keys": len(p_idx),
        "child_distinct_fk_keys": len(c_idx),
        "matched_distinct_keys": len(matched_keys),
        "orphan_distinct_keys": len(orphan_keys),
        "matched_child_rows": matched_child_rows,
        "orphan_child_rows": orphan_child_rows,
        "match_rate_on_complete_rows": (matched_child_rows / child_complete) if child_complete else 0.0,
        "parent_key_coverage": (parent_keys_referenced / len(p_idx)) if p_idx else 0.0,
        "avg_children_per_parent": avg_children_per_parent,
        "max_children_per_parent": max_children_per_parent,
    }


def validate_fk(child_rows, child_cols, parent_rows, parent_cols):
    c_idx = build_index(child_rows, child_cols)
    p_idx = build_index(parent_rows, parent_cols)

    child_total = len(child_rows)
    child_complete = sum(len(v) for v in c_idx.values())
    child_null = child_total - child_complete

    matched_keys = set(c_idx.keys()) & set(p_idx.keys())
    orphan_keys = set(c_idx.keys()) - set(p_idx.keys())

    matched_child_rows = sum(len(c_idx[k]) for k in matched_keys)
    orphan_child_rows = sum(len(c_idx[k]) for k in orphan_keys)

    parent_keys_referenced = len(matched_keys)

    fanout = []
    for k in matched_keys:
        fanout.append(len(c_idx[k]))

    if fanout:
        avg_children_per_parent = sum(fanout) / len(fanout)
        max_children_per_parent = max(fanout)
    else:
        avg_children_per_parent = 0.0
        max_children_per_parent = 0

    return {
        "child_total_rows": child_total,
        "child_complete_fk_rows": child_complete,
        "child_null_fk_rows": child_null,
        "parent_distinct_keys": len(p_idx),
        "child_distinct_fk_keys": len(c_idx),
        "matched_distinct_keys": len(matched_keys),
        "orphan_distinct_keys": len(orphan_keys),
        "matched_child_rows": matched_child_rows,
        "orphan_child_rows": orphan_child_rows,
        "match_rate_on_complete_rows": (matched_child_rows / child_complete) if child_complete else 0.0,
        "parent_key_coverage": (parent_keys_referenced / len(p_idx)) if p_idx else 0.0,
        "avg_children_per_parent": avg_children_per_parent,
        "max_children_per_parent": max_children_per_parent,
    }


def main():
    data = {e: read_jsonl(e) for e in ENTITIES}

    # Candidate keys to verify uniqueness (based on actual data, not naming only).
    key_candidates = {
        "sales_order_headers": [["salesOrder"]],
        "sales_order_items": [["salesOrder", "salesOrderItem"]],
        "sales_order_schedule_lines": [["salesOrder", "salesOrderItem", "scheduleLine"]],
        "outbound_delivery_headers": [["deliveryDocument"]],
        "outbound_delivery_items": [["deliveryDocument", "deliveryDocumentItem"]],
        "billing_document_headers": [["billingDocument"]],
        "billing_document_items": [["billingDocument", "billingDocumentItem"]],
        "billing_document_cancellations": [["billingDocument"]],
        "payments_accounts_receivable": [["accountingDocument"], ["accountingDocument", "accountingDocumentItem"]],
        "journal_entry_items_accounts_receivable": [["accountingDocument"], ["accountingDocument", "accountingDocumentItem"]],
        "business_partners": [["businessPartner"], ["customer"]],
        "business_partner_addresses": [["businessPartner"], ["addressId"], ["addressUuid"]],
        "customer_company_assignments": [["customer"], ["customer", "companyCode"]],
        "customer_sales_area_assignments": [["customer", "salesOrganization", "distributionChannel", "division"]],
        "products": [["product"]],
        "product_descriptions": [["product"], ["product", "language"]],
        "plants": [["plant"]],
        "product_plants": [["product", "plant"]],
        "product_storage_locations": [["product", "plant", "storageLocation"]],
    }

    key_results = {}
    for e, combos in key_candidates.items():
        key_results[e] = []
        rows = data[e]
        for cols in combos:
            key_results[e].append({
                "columns": cols,
                "stats": key_stats(rows, cols),
            })

    # FK candidates focused on high-confidence process/master-data links.
    fk_candidates = [
        {
            "name": "sales_order_items.salesOrder -> sales_order_headers.salesOrder",
            "child": ("sales_order_items", ["salesOrder"]),
            "parent": ("sales_order_headers", ["salesOrder"]),
        },
        {
            "name": "sales_order_schedule_lines.(salesOrder,salesOrderItem) -> sales_order_items.(salesOrder,salesOrderItem)",
            "child": ("sales_order_schedule_lines", ["salesOrder", "salesOrderItem"]),
            "parent": ("sales_order_items", ["salesOrder", "salesOrderItem"]),
        },
        {
            "name": "outbound_delivery_items.deliveryDocument -> outbound_delivery_headers.deliveryDocument",
            "child": ("outbound_delivery_items", ["deliveryDocument"]),
            "parent": ("outbound_delivery_headers", ["deliveryDocument"]),
        },
        {
            "name": "outbound_delivery_items.referenceSdDocument -> sales_order_headers.salesOrder",
            "child": ("outbound_delivery_items", ["referenceSdDocument"]),
            "parent": ("sales_order_headers", ["salesOrder"]),
        },
        {
            "name": "outbound_delivery_items.(referenceSdDocument,referenceSdDocumentItem) -> sales_order_items.(salesOrder,salesOrderItem)",
            "child": ("outbound_delivery_items", ["referenceSdDocument", "referenceSdDocumentItem"]),
            "parent": ("sales_order_items", ["salesOrder", "salesOrderItem"]),
        },
        {
            "name": "billing_document_items.billingDocument -> billing_document_headers.billingDocument",
            "child": ("billing_document_items", ["billingDocument"]),
            "parent": ("billing_document_headers", ["billingDocument"]),
        },
        {
            "name": "billing_document_items.referenceSdDocument -> outbound_delivery_headers.deliveryDocument",
            "child": ("billing_document_items", ["referenceSdDocument"]),
            "parent": ("outbound_delivery_headers", ["deliveryDocument"]),
        },
        {
            "name": "billing_document_items.(referenceSdDocument,referenceSdDocumentItem) -> outbound_delivery_items.(deliveryDocument,deliveryDocumentItem)",
            "child": ("billing_document_items", ["referenceSdDocument", "referenceSdDocumentItem"]),
            "parent": ("outbound_delivery_items", ["deliveryDocument", "deliveryDocumentItem"]),
        },
        {
            "name": "billing_document_headers.cancelledBillingDocument -> billing_document_cancellations.billingDocument",
            "child": ("billing_document_headers", ["cancelledBillingDocument"]),
            "parent": ("billing_document_cancellations", ["billingDocument"]),
        },
        {
            "name": "billing_document_headers.accountingDocument -> payments_accounts_receivable.accountingDocument",
            "child": ("billing_document_headers", ["accountingDocument"]),
            "parent": ("payments_accounts_receivable", ["accountingDocument"]),
        },
        {
            "name": "billing_document_headers.accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument",
            "child": ("billing_document_headers", ["accountingDocument"]),
            "parent": ("journal_entry_items_accounts_receivable", ["accountingDocument"]),
        },
        {
            "name": "journal_entry_items_accounts_receivable.referenceDocument -> billing_document_headers.billingDocument",
            "child": ("journal_entry_items_accounts_receivable", ["referenceDocument"]),
            "parent": ("billing_document_headers", ["billingDocument"]),
        },
        {
            "name": "payments_accounts_receivable.customer -> business_partners.businessPartner",
            "child": ("payments_accounts_receivable", ["customer"]),
            "parent": ("business_partners", ["businessPartner"]),
        },
        {
            "name": "sales_order_headers.soldToParty -> business_partners.businessPartner",
            "child": ("sales_order_headers", ["soldToParty"]),
            "parent": ("business_partners", ["businessPartner"]),
        },
        {
            "name": "sales_order_items.material -> products.product",
            "child": ("sales_order_items", ["material"]),
            "parent": ("products", ["product"]),
        },
        {
            "name": "outbound_delivery_items.plant -> plants.plant",
            "child": ("outbound_delivery_items", ["plant"]),
            "parent": ("plants", ["plant"]),
        },
        {
            "name": "product_plants.product -> products.product",
            "child": ("product_plants", ["product"]),
            "parent": ("products", ["product"]),
        },
        {
            "name": "product_plants.plant -> plants.plant",
            "child": ("product_plants", ["plant"]),
            "parent": ("plants", ["plant"]),
        },
        {
            "name": "product_storage_locations.(product,plant) -> product_plants.(product,plant)",
            "child": ("product_storage_locations", ["product", "plant"]),
            "parent": ("product_plants", ["product", "plant"]),
        },
    ]

    fk_results = []
    for fk in fk_candidates:
        child_entity, child_cols = fk["child"]
        parent_entity, parent_cols = fk["parent"]
        stats = validate_fk(
            data[child_entity], child_cols,
            data[parent_entity], parent_cols,
        )
        fk_results.append({
            "name": fk["name"],
            "child_entity": child_entity,
            "child_cols": child_cols,
            "parent_entity": parent_entity,
            "parent_cols": parent_cols,
            "stats": stats,
        })

    # Normalized item-level FKs where left-zero padding differs across entities.
    normalized_fk_candidates = [
        {
            "name": "outbound_delivery_items.(referenceSdDocument,referenceSdDocumentItem[norm]) -> sales_order_items.(salesOrder,salesOrderItem[norm])",
            "child": ("outbound_delivery_items", ["referenceSdDocument", "referenceSdDocumentItem"]),
            "parent": ("sales_order_items", ["salesOrder", "salesOrderItem"]),
            "child_norm": {"referenceSdDocumentItem": normalize_item},
            "parent_norm": {"salesOrderItem": normalize_item},
        },
        {
            "name": "billing_document_items.(referenceSdDocument,referenceSdDocumentItem[norm]) -> outbound_delivery_items.(deliveryDocument,deliveryDocumentItem[norm])",
            "child": ("billing_document_items", ["referenceSdDocument", "referenceSdDocumentItem"]),
            "parent": ("outbound_delivery_items", ["deliveryDocument", "deliveryDocumentItem"]),
            "child_norm": {"referenceSdDocumentItem": normalize_item},
            "parent_norm": {"deliveryDocumentItem": normalize_item},
        },
    ]

    normalized_fk_results = []
    for fk in normalized_fk_candidates:
        child_entity, child_cols = fk["child"]
        parent_entity, parent_cols = fk["parent"]
        stats = validate_fk_with_normalizers(
            data[child_entity], child_cols,
            data[parent_entity], parent_cols,
            fk.get("child_norm"), fk.get("parent_norm"),
        )
        normalized_fk_results.append({
            "name": fk["name"],
            "child_entity": child_entity,
            "child_cols": child_cols,
            "parent_entity": parent_entity,
            "parent_cols": parent_cols,
            "stats": stats,
        })

    # Process flow integrity checks.
    soh_keys = set(build_index(data["sales_order_headers"], ["salesOrder"]).keys())
    soh_item_keys = set(build_index(data["sales_order_items"], ["salesOrder", "salesOrderItem"]).keys())
    odh_keys = set(build_index(data["outbound_delivery_headers"], ["deliveryDocument"]).keys())
    odi_keys = set(build_index(data["outbound_delivery_items"], ["deliveryDocument", "deliveryDocumentItem"]).keys())
    bdh_keys = set(build_index(data["billing_document_headers"], ["billingDocument"]).keys())
    bdi_keys = set(build_index(data["billing_document_items"], ["billingDocument", "billingDocumentItem"]).keys())
    par_keys = set(build_index(data["payments_accounts_receivable"], ["accountingDocument"]).keys())
    jei_acc_keys = set(build_index(data["journal_entry_items_accounts_receivable"], ["accountingDocument"]).keys())

    order_from_delivery = set(build_index(data["outbound_delivery_items"], ["referenceSdDocument"]).keys())
    delivery_from_billing = set(build_index(data["billing_document_items"], ["referenceSdDocument"]).keys())
    billing_from_journal_ref = set(build_index(data["journal_entry_items_accounts_receivable"], ["referenceDocument"]).keys())

    accounting_from_billing = set(build_index(data["billing_document_headers"], ["accountingDocument"]).keys())

    flow_metrics = {
        "orders_total": len(soh_keys),
        "orders_with_delivery": len(soh_keys & order_from_delivery),
        "orders_without_delivery": len(soh_keys - order_from_delivery),
        "deliveries_total": len(odh_keys),
        "deliveries_with_billing": len(odh_keys & delivery_from_billing),
        "deliveries_without_billing": len(odh_keys - delivery_from_billing),
        "billings_total": len(bdh_keys),
        "billings_with_journal_ref": len(bdh_keys & billing_from_journal_ref),
        "billings_without_journal_ref": len(bdh_keys - billing_from_journal_ref),
        "billing_accounting_docs_total": len(accounting_from_billing),
        "billing_accounting_docs_with_payment": len(accounting_from_billing & par_keys),
        "billing_accounting_docs_without_payment": len(accounting_from_billing - par_keys),
        "billing_accounting_docs_with_journal_acc": len(accounting_from_billing & jei_acc_keys),
        "billing_accounting_docs_without_journal_acc": len(accounting_from_billing - jei_acc_keys),
        "order_item_total": len(soh_item_keys),
        "delivery_item_total": len(odi_keys),
        "billing_item_total": len(bdi_keys),
    }

    # Sample trace extraction with strict item-level chain checks.
    by_odi_ref_item = build_index_with_normalizer(
        data["outbound_delivery_items"],
        ["referenceSdDocument", "referenceSdDocumentItem"],
        {"referenceSdDocumentItem": normalize_item},
    )
    by_bdi_ref_item = build_index_with_normalizer(
        data["billing_document_items"],
        ["referenceSdDocument", "referenceSdDocumentItem"],
        {"referenceSdDocumentItem": normalize_item},
    )
    by_bdh = build_index(data["billing_document_headers"], ["billingDocument"])
    by_par = build_index(data["payments_accounts_receivable"], ["accountingDocument"])
    by_jei_acc = build_index(data["journal_entry_items_accounts_receivable"], ["accountingDocument"])
    by_jei_ref = build_index(data["journal_entry_items_accounts_receivable"], ["referenceDocument"])

    sample_traces = []
    for so_item_key in sorted(soh_item_keys):
        odi_rows = by_odi_ref_item.get(so_item_key, [])
        if not odi_rows:
            continue
        bdi_rows = []
        for odi in odi_rows:
            did = odi.get("deliveryDocument")
            di = normalize_item(odi.get("deliveryDocumentItem"))
            if did is None or di is None:
                continue
            bdi_rows.extend(by_bdi_ref_item.get(f"{did}|{di}", []))
        if not bdi_rows:
            continue

        billing_docs = sorted({str(r.get("billingDocument")) for r in bdi_rows if r.get("billingDocument") is not None})
        if not billing_docs:
            continue

        accounting_docs = set()
        payments = set()
        journals = set()
        for bd in billing_docs:
            for bh in by_bdh.get(bd, []):
                ad = bh.get("accountingDocument")
                if ad is None:
                    continue
                ad = str(ad)
                accounting_docs.add(ad)
                for p in by_par.get(ad, []):
                    payments.add(str(p.get("accountingDocument")))
                for j in by_jei_acc.get(ad, []):
                    journals.add(str(j.get("accountingDocument")))
            for j in by_jei_ref.get(bd, []):
                ad2 = j.get("accountingDocument")
                if ad2 is not None:
                    journals.add(str(ad2))

        if accounting_docs and (payments or journals):
            so, so_item = so_item_key.split("|", 1)
            sample_traces.append({
                "salesOrder": so,
                "salesOrderItem": so_item,
                "deliveries": sorted({str(r.get("deliveryDocument")) for r in odi_rows if r.get("deliveryDocument") is not None}),
                "deliveryItems": sorted({str(r.get("deliveryDocumentItem")) for r in odi_rows if r.get("deliveryDocumentItem") is not None}),
                "billingDocuments": billing_docs,
                "accountingDocuments": sorted(accounting_docs),
                "payments": sorted({x for x in payments if x and x != "None"}),
                "journals": sorted({x for x in journals if x and x != "None"}),
            })
        if len(sample_traces) >= 3:
            break

    result = {
        "key_validation": key_results,
        "fk_validation": fk_results,
        "normalized_fk_validation": normalized_fk_results,
        "flow_metrics": flow_metrics,
        "sample_traces": sample_traces,
    }

    (OUT / "fk_flow_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Human-readable refined report.
    lines = []
    lines.append("# Refined Dataset Analysis (FK + Business Flow Verification)")
    lines.append("")
    lines.append("## Method")
    lines.append("- All joins are validated using exact value matching over all rows, not sampled inference.")
    lines.append("- FK quality metrics include match rate, orphan counts, and parent-key coverage.")
    lines.append("- Business flow checks use both document-level and item-level references where available.")
    lines.append("")

    lines.append("## Key Validation")
    lines.append("")
    for entity in ENTITIES:
        lines.append(f"### {entity}")
        for item in key_results[entity]:
            cols = ",".join(item["columns"])
            st = item["stats"]
            lines.append(
                f"- key({cols}): strict={st['is_strict_key']}, unique_on_complete_rows={st['is_unique_on_complete_rows']}, complete_rows={st['complete_rows']}/{st['total_rows']}, duplicate_complete_rows={st['duplicate_complete_rows']}"
            )
        lines.append("")

    lines.append("## Foreign Key Validation")
    lines.append("")
    for fk in fk_results:
        s = fk["stats"]
        lines.append(f"### {fk['name']}")
        lines.append(
            f"- complete_fk_rows={s['child_complete_fk_rows']}/{s['child_total_rows']}, matched_child_rows={s['matched_child_rows']}, orphan_child_rows={s['orphan_child_rows']}, match_rate={s['match_rate_on_complete_rows']:.2%}"
        )
        lines.append(
            f"- distinct_fk_keys={s['child_distinct_fk_keys']}, matched_distinct_keys={s['matched_distinct_keys']}, orphan_distinct_keys={s['orphan_distinct_keys']}"
        )
        lines.append(
            f"- parent_keys={s['parent_distinct_keys']}, parent_key_coverage={s['parent_key_coverage']:.2%}, avg_children_per_parent={s['avg_children_per_parent']:.2f}, max_children_per_parent={s['max_children_per_parent']}"
        )
        lines.append("")

    lines.append("## Normalized Foreign Key Validation")
    lines.append("")
    lines.append("- Note: item-level codes are left-zero padded in some entities (e.g., 000010) and unpadded in others (e.g., 10).")
    lines.append("- The checks below normalize item numbers before join validation.")
    lines.append("")
    for fk in normalized_fk_results:
        s = fk["stats"]
        lines.append(f"### {fk['name']}")
        lines.append(
            f"- complete_fk_rows={s['child_complete_fk_rows']}/{s['child_total_rows']}, matched_child_rows={s['matched_child_rows']}, orphan_child_rows={s['orphan_child_rows']}, match_rate={s['match_rate_on_complete_rows']:.2%}"
        )
        lines.append(
            f"- distinct_fk_keys={s['child_distinct_fk_keys']}, matched_distinct_keys={s['matched_distinct_keys']}, orphan_distinct_keys={s['orphan_distinct_keys']}"
        )
        lines.append(
            f"- parent_keys={s['parent_distinct_keys']}, parent_key_coverage={s['parent_key_coverage']:.2%}, avg_children_per_parent={s['avg_children_per_parent']:.2f}, max_children_per_parent={s['max_children_per_parent']}"
        )
        lines.append("")

    lines.append("## Business Flow Correctness")
    lines.append("")
    fm = flow_metrics
    lines.append(f"- Orders total: {fm['orders_total']}")
    lines.append(f"- Orders with delivery: {fm['orders_with_delivery']} ({(fm['orders_with_delivery']/fm['orders_total'] if fm['orders_total'] else 0):.2%})")
    lines.append(f"- Orders without delivery: {fm['orders_without_delivery']}")
    lines.append("")
    lines.append(f"- Deliveries total: {fm['deliveries_total']}")
    lines.append(f"- Deliveries with billing: {fm['deliveries_with_billing']} ({(fm['deliveries_with_billing']/fm['deliveries_total'] if fm['deliveries_total'] else 0):.2%})")
    lines.append(f"- Deliveries without billing: {fm['deliveries_without_billing']}")
    lines.append("")
    lines.append(f"- Billings total: {fm['billings_total']}")
    lines.append(f"- Billings with journal (referenceDocument): {fm['billings_with_journal_ref']} ({(fm['billings_with_journal_ref']/fm['billings_total'] if fm['billings_total'] else 0):.2%})")
    lines.append(f"- Billings without journal (referenceDocument): {fm['billings_without_journal_ref']}")
    lines.append("")
    lines.append(f"- Billing accounting docs total: {fm['billing_accounting_docs_total']}")
    lines.append(f"- Billing accounting docs with payment: {fm['billing_accounting_docs_with_payment']} ({(fm['billing_accounting_docs_with_payment']/fm['billing_accounting_docs_total'] if fm['billing_accounting_docs_total'] else 0):.2%})")
    lines.append(f"- Billing accounting docs without payment: {fm['billing_accounting_docs_without_payment']}")
    lines.append(f"- Billing accounting docs with journal (accountingDocument): {fm['billing_accounting_docs_with_journal_acc']} ({(fm['billing_accounting_docs_with_journal_acc']/fm['billing_accounting_docs_total'] if fm['billing_accounting_docs_total'] else 0):.2%})")
    lines.append(f"- Billing accounting docs without journal (accountingDocument): {fm['billing_accounting_docs_without_journal_acc']}")
    lines.append("")

    lines.append("## Sample Verified Item-Level Traces")
    lines.append("")
    if not sample_traces:
        lines.append("- No full item-level traces found with both downstream financial links.")
    else:
        for i, t in enumerate(sample_traces, start=1):
            lines.append(
                f"- Trace {i}: SO={t['salesOrder']} item={t['salesOrderItem']} -> deliveries={','.join(t['deliveries'])} -> billing={','.join(t['billingDocuments'])} -> accounting={','.join(t['accountingDocuments'])} -> payments={','.join(t['payments']) if t['payments'] else 'none'} -> journals={','.join(t['journals']) if t['journals'] else 'none'}"
            )

    (OUT / "dataset_analysis_refined.md").write_text("\n".join(lines), encoding="utf-8")

    print("Wrote analysis_output/fk_flow_validation.json")
    print("Wrote analysis_output/dataset_analysis_refined.md")


if __name__ == "__main__":
    main()
