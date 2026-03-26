# Refined Dataset Analysis (FK + Business Flow Verification)

## Method
- All joins are validated using exact value matching over all rows, not sampled inference.
- FK quality metrics include match rate, orphan counts, and parent-key coverage.
- Business flow checks use both document-level and item-level references where available.

## Key Validation

### sales_order_headers
- key(salesOrder): strict=True, unique_on_complete_rows=True, complete_rows=100/100, duplicate_complete_rows=0

### sales_order_items
- key(salesOrder,salesOrderItem): strict=True, unique_on_complete_rows=True, complete_rows=167/167, duplicate_complete_rows=0

### sales_order_schedule_lines
- key(salesOrder,salesOrderItem,scheduleLine): strict=True, unique_on_complete_rows=True, complete_rows=179/179, duplicate_complete_rows=0

### outbound_delivery_headers
- key(deliveryDocument): strict=True, unique_on_complete_rows=True, complete_rows=86/86, duplicate_complete_rows=0

### outbound_delivery_items
- key(deliveryDocument,deliveryDocumentItem): strict=True, unique_on_complete_rows=True, complete_rows=137/137, duplicate_complete_rows=0

### billing_document_headers
- key(billingDocument): strict=True, unique_on_complete_rows=True, complete_rows=163/163, duplicate_complete_rows=0

### billing_document_items
- key(billingDocument,billingDocumentItem): strict=True, unique_on_complete_rows=True, complete_rows=245/245, duplicate_complete_rows=0

### billing_document_cancellations
- key(billingDocument): strict=True, unique_on_complete_rows=True, complete_rows=80/80, duplicate_complete_rows=0

### payments_accounts_receivable
- key(accountingDocument): strict=True, unique_on_complete_rows=True, complete_rows=120/120, duplicate_complete_rows=0
- key(accountingDocument,accountingDocumentItem): strict=True, unique_on_complete_rows=True, complete_rows=120/120, duplicate_complete_rows=0

### journal_entry_items_accounts_receivable
- key(accountingDocument): strict=True, unique_on_complete_rows=True, complete_rows=123/123, duplicate_complete_rows=0
- key(accountingDocument,accountingDocumentItem): strict=True, unique_on_complete_rows=True, complete_rows=123/123, duplicate_complete_rows=0

### business_partners
- key(businessPartner): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0
- key(customer): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0

### business_partner_addresses
- key(businessPartner): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0
- key(addressId): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0
- key(addressUuid): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0

### customer_company_assignments
- key(customer): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0
- key(customer,companyCode): strict=True, unique_on_complete_rows=True, complete_rows=8/8, duplicate_complete_rows=0

### customer_sales_area_assignments
- key(customer,salesOrganization,distributionChannel,division): strict=True, unique_on_complete_rows=True, complete_rows=28/28, duplicate_complete_rows=0

### products
- key(product): strict=True, unique_on_complete_rows=True, complete_rows=69/69, duplicate_complete_rows=0

### product_descriptions
- key(product): strict=True, unique_on_complete_rows=True, complete_rows=69/69, duplicate_complete_rows=0
- key(product,language): strict=True, unique_on_complete_rows=True, complete_rows=69/69, duplicate_complete_rows=0

### plants
- key(plant): strict=True, unique_on_complete_rows=True, complete_rows=44/44, duplicate_complete_rows=0

### product_plants
- key(product,plant): strict=True, unique_on_complete_rows=True, complete_rows=3036/3036, duplicate_complete_rows=0

### product_storage_locations
- key(product,plant,storageLocation): strict=True, unique_on_complete_rows=True, complete_rows=16723/16723, duplicate_complete_rows=0

## Foreign Key Validation

### sales_order_items.salesOrder -> sales_order_headers.salesOrder
- complete_fk_rows=167/167, matched_child_rows=167, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=100, matched_distinct_keys=100, orphan_distinct_keys=0
- parent_keys=100, parent_key_coverage=100.00%, avg_children_per_parent=1.67, max_children_per_parent=12

### sales_order_schedule_lines.(salesOrder,salesOrderItem) -> sales_order_items.(salesOrder,salesOrderItem)
- complete_fk_rows=179/179, matched_child_rows=179, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=167, matched_distinct_keys=167, orphan_distinct_keys=0
- parent_keys=167, parent_key_coverage=100.00%, avg_children_per_parent=1.07, max_children_per_parent=2

### outbound_delivery_items.deliveryDocument -> outbound_delivery_headers.deliveryDocument
- complete_fk_rows=137/137, matched_child_rows=137, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=86, matched_distinct_keys=86, orphan_distinct_keys=0
- parent_keys=86, parent_key_coverage=100.00%, avg_children_per_parent=1.59, max_children_per_parent=12

### outbound_delivery_items.referenceSdDocument -> sales_order_headers.salesOrder
- complete_fk_rows=137/137, matched_child_rows=137, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=86, matched_distinct_keys=86, orphan_distinct_keys=0
- parent_keys=100, parent_key_coverage=86.00%, avg_children_per_parent=1.59, max_children_per_parent=12

### outbound_delivery_items.(referenceSdDocument,referenceSdDocumentItem) -> sales_order_items.(salesOrder,salesOrderItem)
- complete_fk_rows=137/137, matched_child_rows=0, orphan_child_rows=137, match_rate=0.00%
- distinct_fk_keys=137, matched_distinct_keys=0, orphan_distinct_keys=137
- parent_keys=167, parent_key_coverage=0.00%, avg_children_per_parent=0.00, max_children_per_parent=0

### billing_document_items.billingDocument -> billing_document_headers.billingDocument
- complete_fk_rows=245/245, matched_child_rows=245, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=163, matched_distinct_keys=163, orphan_distinct_keys=0
- parent_keys=163, parent_key_coverage=100.00%, avg_children_per_parent=1.50, max_children_per_parent=12

### billing_document_items.referenceSdDocument -> outbound_delivery_headers.deliveryDocument
- complete_fk_rows=245/245, matched_child_rows=245, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=83, matched_distinct_keys=83, orphan_distinct_keys=0
- parent_keys=86, parent_key_coverage=96.51%, avg_children_per_parent=2.95, max_children_per_parent=24

### billing_document_items.(referenceSdDocument,referenceSdDocumentItem) -> outbound_delivery_items.(deliveryDocument,deliveryDocumentItem)
- complete_fk_rows=245/245, matched_child_rows=0, orphan_child_rows=245, match_rate=0.00%
- distinct_fk_keys=124, matched_distinct_keys=0, orphan_distinct_keys=124
- parent_keys=137, parent_key_coverage=0.00%, avg_children_per_parent=0.00, max_children_per_parent=0

### billing_document_headers.cancelledBillingDocument -> billing_document_cancellations.billingDocument
- complete_fk_rows=163/163, matched_child_rows=80, orphan_child_rows=83, match_rate=49.08%
- distinct_fk_keys=81, matched_distinct_keys=80, orphan_distinct_keys=1
- parent_keys=80, parent_key_coverage=100.00%, avg_children_per_parent=1.00, max_children_per_parent=1

### billing_document_headers.accountingDocument -> payments_accounts_receivable.accountingDocument
- complete_fk_rows=163/163, matched_child_rows=120, orphan_child_rows=43, match_rate=73.62%
- distinct_fk_keys=163, matched_distinct_keys=120, orphan_distinct_keys=43
- parent_keys=120, parent_key_coverage=100.00%, avg_children_per_parent=1.00, max_children_per_parent=1

### billing_document_headers.accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument
- complete_fk_rows=163/163, matched_child_rows=123, orphan_child_rows=40, match_rate=75.46%
- distinct_fk_keys=163, matched_distinct_keys=123, orphan_distinct_keys=40
- parent_keys=123, parent_key_coverage=100.00%, avg_children_per_parent=1.00, max_children_per_parent=1

### journal_entry_items_accounts_receivable.referenceDocument -> billing_document_headers.billingDocument
- complete_fk_rows=123/123, matched_child_rows=123, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=123, matched_distinct_keys=123, orphan_distinct_keys=0
- parent_keys=163, parent_key_coverage=75.46%, avg_children_per_parent=1.00, max_children_per_parent=1

### payments_accounts_receivable.customer -> business_partners.businessPartner
- complete_fk_rows=120/120, matched_child_rows=120, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=2, matched_distinct_keys=2, orphan_distinct_keys=0
- parent_keys=8, parent_key_coverage=25.00%, avg_children_per_parent=60.00, max_children_per_parent=106

### sales_order_headers.soldToParty -> business_partners.businessPartner
- complete_fk_rows=100/100, matched_child_rows=100, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=8, matched_distinct_keys=8, orphan_distinct_keys=0
- parent_keys=8, parent_key_coverage=100.00%, avg_children_per_parent=12.50, max_children_per_parent=72

### sales_order_items.material -> products.product
- complete_fk_rows=167/167, matched_child_rows=167, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=69, matched_distinct_keys=69, orphan_distinct_keys=0
- parent_keys=69, parent_key_coverage=100.00%, avg_children_per_parent=2.42, max_children_per_parent=11

### outbound_delivery_items.plant -> plants.plant
- complete_fk_rows=137/137, matched_child_rows=137, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=5, matched_distinct_keys=5, orphan_distinct_keys=0
- parent_keys=44, parent_key_coverage=11.36%, avg_children_per_parent=27.40, max_children_per_parent=110

### product_plants.product -> products.product
- complete_fk_rows=3036/3036, matched_child_rows=3036, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=69, matched_distinct_keys=69, orphan_distinct_keys=0
- parent_keys=69, parent_key_coverage=100.00%, avg_children_per_parent=44.00, max_children_per_parent=44

### product_plants.plant -> plants.plant
- complete_fk_rows=3036/3036, matched_child_rows=3036, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=44, matched_distinct_keys=44, orphan_distinct_keys=0
- parent_keys=44, parent_key_coverage=100.00%, avg_children_per_parent=69.00, max_children_per_parent=69

### product_storage_locations.(product,plant) -> product_plants.(product,plant)
- complete_fk_rows=16723/16723, matched_child_rows=16723, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=3021, matched_distinct_keys=3021, orphan_distinct_keys=0
- parent_keys=3036, parent_key_coverage=99.51%, avg_children_per_parent=5.54, max_children_per_parent=20

## Normalized Foreign Key Validation

- Note: item-level codes are left-zero padded in some entities (e.g., 000010) and unpadded in others (e.g., 10).
- The checks below normalize item numbers before join validation.

### outbound_delivery_items.(referenceSdDocument,referenceSdDocumentItem[norm]) -> sales_order_items.(salesOrder,salesOrderItem[norm])
- complete_fk_rows=137/137, matched_child_rows=137, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=137, matched_distinct_keys=137, orphan_distinct_keys=0
- parent_keys=167, parent_key_coverage=82.04%, avg_children_per_parent=1.00, max_children_per_parent=1

### billing_document_items.(referenceSdDocument,referenceSdDocumentItem[norm]) -> outbound_delivery_items.(deliveryDocument,deliveryDocumentItem[norm])
- complete_fk_rows=245/245, matched_child_rows=245, orphan_child_rows=0, match_rate=100.00%
- distinct_fk_keys=124, matched_distinct_keys=124, orphan_distinct_keys=0
- parent_keys=137, parent_key_coverage=90.51%, avg_children_per_parent=1.98, max_children_per_parent=2

## Business Flow Correctness

- Orders total: 100
- Orders with delivery: 86 (86.00%)
- Orders without delivery: 14

- Deliveries total: 86
- Deliveries with billing: 83 (96.51%)
- Deliveries without billing: 3

- Billings total: 163
- Billings with journal (referenceDocument): 123 (75.46%)
- Billings without journal (referenceDocument): 40

- Billing accounting docs total: 163
- Billing accounting docs with payment: 120 (73.62%)
- Billing accounting docs without payment: 43
- Billing accounting docs with journal (accountingDocument): 123 (75.46%)
- Billing accounting docs without journal (accountingDocument): 40

## Sample Verified Item-Level Traces

- Trace 1: SO=740509 item=10 -> deliveries=80738040 -> billing=90504204,91150217 -> accounting=9400000205,9400635988 -> payments=9400000205,9400635988 -> journals=9400000205,9400635988
- Trace 2: SO=740510 item=10 -> deliveries=80738041 -> billing=90504206,91150216 -> accounting=9400000206,9400635987 -> payments=9400000206,9400635987 -> journals=9400000206,9400635987
- Trace 3: SO=740511 item=10 -> deliveries=80738042 -> billing=90504207,91150215 -> accounting=9400000208,9400635986 -> payments=9400000208,9400635986 -> journals=9400000208,9400635986