# Dataset Analysis Report

## Entities

### Entity: billing_document_cancellations
- Records: 80
- Likely primary key: billingDocument
- Fields:
  - accountingDocument: string; null_ratio=0.00%
  - billingDocument: string; null_ratio=0.00% [primary key]
  - billingDocumentDate: datetime; null_ratio=0.00%
  - billingDocumentIsCancelled: bool; null_ratio=0.00%
  - billingDocumentType: string; null_ratio=0.00%
  - cancelledBillingDocument: string; null_ratio=0.00%
  - companyCode: string; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - creationTime: object; null_ratio=0.00%
  - fiscalYear: string; null_ratio=0.00%
  - lastChangeDateTime: datetime; null_ratio=0.00%
  - soldToParty: string; null_ratio=0.00%
  - totalNetAmount: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - billingDocument -> billing_document_headers.billingDocument (source coverage=100.0%, overlap=80)
  - soldToParty -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=4)
  - soldToParty -> business_partners.businessPartner (source coverage=100.0%, overlap=4)
  - soldToParty -> customer_company_assignments.customer (source coverage=100.0%, overlap=4)
  - accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument (source coverage=80.0%, overlap=64)
  - accountingDocument -> payments_accounts_receivable.accountingDocument (source coverage=80.0%, overlap=64)

### Entity: billing_document_headers
- Records: 163
- Likely primary key: billingDocument
- Fields:
  - accountingDocument: string; null_ratio=0.00%
  - billingDocument: string; null_ratio=0.00% [primary key]
  - billingDocumentDate: datetime; null_ratio=0.00%
  - billingDocumentIsCancelled: bool; null_ratio=0.00%
  - billingDocumentType: string; null_ratio=0.00%
  - cancelledBillingDocument: string; null_ratio=0.00%
  - companyCode: string; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - creationTime: object; null_ratio=0.00%
  - fiscalYear: string; null_ratio=0.00%
  - lastChangeDateTime: datetime; null_ratio=0.00%
  - soldToParty: string; null_ratio=0.00%
  - totalNetAmount: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - soldToParty -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=4)
  - soldToParty -> business_partners.businessPartner (source coverage=100.0%, overlap=4)
  - soldToParty -> customer_company_assignments.customer (source coverage=100.0%, overlap=4)
  - cancelledBillingDocument -> billing_document_cancellations.billingDocument (source coverage=98.8%, overlap=80)
  - accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument (source coverage=75.5%, overlap=123)
  - accountingDocument -> payments_accounts_receivable.accountingDocument (source coverage=73.6%, overlap=120)

### Entity: billing_document_items
- Records: 245
- Likely primary key: billingDocument + billingDocumentItem
- Fields:
  - billingDocument: string; null_ratio=0.00%
  - billingDocumentItem: string; null_ratio=0.00%
  - billingQuantity: string; null_ratio=0.00%
  - billingQuantityUnit: string; null_ratio=0.00%
  - material: string; null_ratio=0.00%
  - netAmount: string; null_ratio=0.00%
  - referenceSdDocument: string; null_ratio=0.00%
  - referenceSdDocumentItem: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - billingDocument -> billing_document_headers.billingDocument (source coverage=100.0%, overlap=163)
  - material -> product_descriptions.product (source coverage=100.0%, overlap=55)
  - material -> products.product (source coverage=100.0%, overlap=55)
  - referenceSdDocument -> outbound_delivery_headers.deliveryDocument (source coverage=100.0%, overlap=83)

### Entity: business_partner_addresses
- Records: 8
- Likely primary key: businessPartner
- Fields:
  - addressId: string; null_ratio=0.00%
  - addressTimeZone: string; null_ratio=0.00%
  - addressUuid: string; null_ratio=0.00%
  - businessPartner: string; null_ratio=0.00% [primary key]
  - cityName: string; null_ratio=0.00%
  - country: string; null_ratio=0.00%
  - poBox: string; null_ratio=0.00%
  - poBoxDeviatingCityName: string; null_ratio=0.00%
  - poBoxDeviatingCountry: string; null_ratio=0.00%
  - poBoxDeviatingRegion: string; null_ratio=0.00%
  - poBoxIsWithoutNumber: bool; null_ratio=0.00%
  - poBoxLobbyName: string; null_ratio=0.00%
  - poBoxPostalCode: string; null_ratio=0.00%
  - postalCode: string; null_ratio=0.00%
  - region: string; null_ratio=0.00%
  - streetName: string; null_ratio=0.00%
  - taxJurisdiction: string; null_ratio=0.00%
  - transportZone: string; null_ratio=0.00%
  - validityEndDate: datetime; null_ratio=0.00%
  - validityStartDate: datetime; null_ratio=0.00%
- Possible foreign keys:
  - businessPartner -> business_partners.businessPartner (source coverage=100.0%, overlap=8)
  - businessPartner -> customer_company_assignments.customer (source coverage=100.0%, overlap=8)

### Entity: business_partners
- Records: 8
- Likely primary key: businessPartner
- Fields:
  - businessPartner: string; null_ratio=0.00% [primary key]
  - businessPartnerCategory: string; null_ratio=0.00%
  - businessPartnerFullName: string; null_ratio=0.00%
  - businessPartnerGrouping: string; null_ratio=0.00%
  - businessPartnerIsBlocked: bool; null_ratio=0.00%
  - businessPartnerName: string; null_ratio=0.00%
  - correspondenceLanguage: string; null_ratio=0.00%
  - createdByUser: string; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - creationTime: object; null_ratio=0.00%
  - customer: string; null_ratio=0.00%
  - firstName: string; null_ratio=0.00%
  - formOfAddress: string; null_ratio=0.00%
  - industry: string; null_ratio=0.00%
  - isMarkedForArchiving: bool; null_ratio=0.00%
  - lastChangeDate: datetime; null_ratio=0.00%
  - lastName: string; null_ratio=0.00%
  - organizationBpName1: string; null_ratio=0.00%
  - organizationBpName2: string; null_ratio=0.00%
- Possible foreign keys:
  - businessPartner -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=8)
  - businessPartner -> customer_company_assignments.customer (source coverage=100.0%, overlap=8)
  - customer -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=8)
  - customer -> customer_company_assignments.customer (source coverage=100.0%, overlap=8)

### Entity: customer_company_assignments
- Records: 8
- Likely primary key: customer
- Fields:
  - accountingClerk: string; null_ratio=0.00%
  - accountingClerkFaxNumber: string; null_ratio=0.00%
  - accountingClerkInternetAddress: string; null_ratio=0.00%
  - accountingClerkPhoneNumber: string; null_ratio=0.00%
  - alternativePayerAccount: string; null_ratio=0.00%
  - companyCode: string; null_ratio=0.00%
  - customer: string; null_ratio=0.00% [primary key]
  - customerAccountGroup: string; null_ratio=0.00%
  - deletionIndicator: bool; null_ratio=0.00%
  - paymentBlockingReason: string; null_ratio=0.00%
  - paymentMethodsList: string; null_ratio=0.00%
  - paymentTerms: string; null_ratio=0.00%
  - reconciliationAccount: string; null_ratio=0.00%
- Possible foreign keys:
  - customer -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=8)
  - customer -> business_partners.businessPartner (source coverage=100.0%, overlap=8)

### Entity: customer_sales_area_assignments
- Records: 28
- Likely primary key: not found (likely composite or no strict PK)
- Fields:
  - billingIsBlockedForCustomer: string; null_ratio=0.00%
  - completeDeliveryIsDefined: bool; null_ratio=0.00%
  - creditControlArea: string; null_ratio=0.00%
  - currency: string; null_ratio=0.00%
  - customer: string; null_ratio=0.00%
  - customerPaymentTerms: string; null_ratio=0.00%
  - deliveryPriority: string; null_ratio=0.00%
  - distributionChannel: string; null_ratio=0.00%
  - division: string; null_ratio=0.00%
  - exchangeRateType: string; null_ratio=0.00%
  - incotermsClassification: string; null_ratio=0.00%
  - incotermsLocation1: string; null_ratio=0.00%
  - salesDistrict: string; null_ratio=0.00%
  - salesGroup: string; null_ratio=0.00%
  - salesOffice: string; null_ratio=0.00%
  - salesOrganization: string; null_ratio=0.00%
  - shippingCondition: string; null_ratio=0.00%
  - slsUnlmtdOvrdelivIsAllwd: bool; null_ratio=0.00%
  - supplyingPlant: string; null_ratio=0.00%
- Possible foreign keys:
  - customer -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=8)
  - customer -> business_partners.businessPartner (source coverage=100.0%, overlap=8)
  - customer -> customer_company_assignments.customer (source coverage=100.0%, overlap=8)

### Entity: journal_entry_items_accounts_receivable
- Records: 123
- Likely primary key: accountingDocument
- Fields:
  - accountingDocument: string; null_ratio=0.00% [primary key]
  - accountingDocumentItem: string; null_ratio=0.00%
  - accountingDocumentType: string; null_ratio=0.00%
  - amountInCompanyCodeCurrency: string; null_ratio=0.00%
  - amountInTransactionCurrency: string; null_ratio=0.00%
  - assignmentReference: string; null_ratio=0.00%
  - clearingAccountingDocument: string; null_ratio=0.00%
  - clearingDate: datetime; null_ratio=2.44%
  - clearingDocFiscalYear: string; null_ratio=0.00%
  - companyCode: string; null_ratio=0.00%
  - companyCodeCurrency: string; null_ratio=0.00%
  - costCenter: string; null_ratio=0.00%
  - customer: string; null_ratio=0.00%
  - documentDate: datetime; null_ratio=0.00%
  - financialAccountType: string; null_ratio=0.00%
  - fiscalYear: string; null_ratio=0.00%
  - glAccount: string; null_ratio=0.00%
  - lastChangeDateTime: datetime; null_ratio=0.00%
  - postingDate: datetime; null_ratio=0.00%
  - profitCenter: string; null_ratio=0.00%
  - referenceDocument: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - customer -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=2)
  - customer -> business_partners.businessPartner (source coverage=100.0%, overlap=2)
  - customer -> customer_company_assignments.customer (source coverage=100.0%, overlap=2)
  - referenceDocument -> billing_document_headers.billingDocument (source coverage=100.0%, overlap=123)
  - accountingDocument -> payments_accounts_receivable.accountingDocument (source coverage=97.6%, overlap=120)
  - clearingAccountingDocument -> payments_accounts_receivable.accountingDocument (source coverage=72.7%, overlap=56)

### Entity: outbound_delivery_headers
- Records: 86
- Likely primary key: deliveryDocument
- Fields:
  - actualGoodsMovementDate: datetime; null_ratio=96.51%
  - actualGoodsMovementTime: object; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - creationTime: object; null_ratio=0.00%
  - deliveryBlockReason: string; null_ratio=0.00%
  - deliveryDocument: string; null_ratio=0.00% [primary key]
  - hdrGeneralIncompletionStatus: string; null_ratio=0.00%
  - headerBillingBlockReason: string; null_ratio=0.00%
  - lastChangeDate: datetime; null_ratio=3.49%
  - overallGoodsMovementStatus: string; null_ratio=0.00%
  - overallPickingStatus: string; null_ratio=0.00%
  - overallProofOfDeliveryStatus: string; null_ratio=0.00%
  - shippingPoint: string; null_ratio=0.00%
- Possible foreign keys:
  - shippingPoint -> plants.plant (source coverage=100.0%, overlap=5)

### Entity: outbound_delivery_items
- Records: 137
- Likely primary key: deliveryDocument + deliveryDocumentItem
- Fields:
  - actualDeliveryQuantity: string; null_ratio=0.00%
  - batch: string; null_ratio=0.00%
  - deliveryDocument: string; null_ratio=0.00%
  - deliveryDocumentItem: string; null_ratio=0.00%
  - deliveryQuantityUnit: string; null_ratio=0.00%
  - itemBillingBlockReason: string; null_ratio=0.00%
  - lastChangeDate: null; null_ratio=100.00%
  - plant: string; null_ratio=0.00%
  - referenceSdDocument: string; null_ratio=0.00%
  - referenceSdDocumentItem: string; null_ratio=0.00%
  - storageLocation: string; null_ratio=0.00%
- Possible foreign keys:
  - deliveryDocument -> outbound_delivery_headers.deliveryDocument (source coverage=100.0%, overlap=86)
  - plant -> plants.plant (source coverage=100.0%, overlap=5)
  - referenceSdDocument -> sales_order_headers.salesOrder (source coverage=100.0%, overlap=86)

### Entity: payments_accounts_receivable
- Records: 120
- Likely primary key: accountingDocument
- Fields:
  - accountingDocument: string; null_ratio=0.00% [primary key]
  - accountingDocumentItem: string; null_ratio=0.00%
  - amountInCompanyCodeCurrency: string; null_ratio=0.00%
  - amountInTransactionCurrency: string; null_ratio=0.00%
  - assignmentReference: null; null_ratio=100.00%
  - clearingAccountingDocument: string; null_ratio=0.00%
  - clearingDate: datetime; null_ratio=0.00%
  - clearingDocFiscalYear: string; null_ratio=0.00%
  - companyCode: string; null_ratio=0.00%
  - companyCodeCurrency: string; null_ratio=0.00%
  - costCenter: null; null_ratio=100.00%
  - customer: string; null_ratio=0.00%
  - documentDate: datetime; null_ratio=0.00%
  - financialAccountType: string; null_ratio=0.00%
  - fiscalYear: string; null_ratio=0.00%
  - glAccount: string; null_ratio=0.00%
  - invoiceReference: null; null_ratio=100.00%
  - invoiceReferenceFiscalYear: null; null_ratio=100.00%
  - postingDate: datetime; null_ratio=0.00%
  - profitCenter: string; null_ratio=0.00%
  - salesDocument: null; null_ratio=100.00%
  - salesDocumentItem: null; null_ratio=100.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument (source coverage=100.0%, overlap=120)
  - customer -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=2)
  - customer -> business_partners.businessPartner (source coverage=100.0%, overlap=2)
  - customer -> customer_company_assignments.customer (source coverage=100.0%, overlap=2)
  - clearingAccountingDocument -> journal_entry_items_accounts_receivable.accountingDocument (source coverage=73.7%, overlap=56)

### Entity: plants
- Records: 44
- Likely primary key: plant
- Fields:
  - addressId: string; null_ratio=0.00%
  - defaultPurchasingOrganization: string; null_ratio=0.00%
  - distributionChannel: string; null_ratio=0.00%
  - division: string; null_ratio=0.00%
  - factoryCalendar: string; null_ratio=0.00%
  - isMarkedForArchiving: bool; null_ratio=0.00%
  - language: string; null_ratio=0.00%
  - plant: string; null_ratio=0.00% [primary key]
  - plantCategory: string; null_ratio=0.00%
  - plantCustomer: string; null_ratio=0.00%
  - plantName: string; null_ratio=0.00%
  - plantSupplier: string; null_ratio=0.00%
  - salesOrganization: string; null_ratio=0.00%
  - valuationArea: string; null_ratio=0.00%

### Entity: product_descriptions
- Records: 69
- Likely primary key: product
- Fields:
  - language: string; null_ratio=0.00%
  - product: string; null_ratio=0.00% [primary key]
  - productDescription: string; null_ratio=0.00%
- Possible foreign keys:
  - product -> products.product (source coverage=100.0%, overlap=69)

### Entity: product_plants
- Records: 3036
- Likely primary key: not found (likely composite or no strict PK)
- Fields:
  - availabilityCheckType: string; null_ratio=0.00%
  - countryOfOrigin: string; null_ratio=0.00%
  - fiscalYearVariant: string; null_ratio=0.00%
  - mrpType: string; null_ratio=0.00%
  - plant: string; null_ratio=0.00%
  - product: string; null_ratio=0.00%
  - productionInvtryManagedLoc: string; null_ratio=0.00%
  - profitCenter: string; null_ratio=0.00%
  - regionOfOrigin: string; null_ratio=0.00%
- Possible foreign keys:
  - plant -> plants.plant (source coverage=100.0%, overlap=44)
  - product -> product_descriptions.product (source coverage=100.0%, overlap=69)
  - product -> products.product (source coverage=100.0%, overlap=69)

### Entity: product_storage_locations
- Records: 16723
- Likely primary key: not found (likely composite or no strict PK)
- Fields:
  - dateOfLastPostedCntUnRstrcdStk: null; null_ratio=100.00%
  - physicalInventoryBlockInd: string; null_ratio=0.00%
  - plant: string; null_ratio=0.00%
  - product: string; null_ratio=0.00%
  - storageLocation: string; null_ratio=0.00%
- Possible foreign keys:
  - plant -> plants.plant (source coverage=100.0%, overlap=44)
  - product -> product_descriptions.product (source coverage=100.0%, overlap=69)
  - product -> products.product (source coverage=100.0%, overlap=69)

### Entity: products
- Records: 69
- Likely primary key: product
- Fields:
  - baseUnit: string; null_ratio=0.00%
  - createdByUser: string; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - crossPlantStatus: string; null_ratio=0.00%
  - crossPlantStatusValidityDate: null; null_ratio=100.00%
  - division: string; null_ratio=0.00%
  - grossWeight: string; null_ratio=0.00%
  - industrySector: string; null_ratio=0.00%
  - isMarkedForDeletion: bool; null_ratio=0.00%
  - lastChangeDate: datetime; null_ratio=0.00%
  - lastChangeDateTime: datetime; null_ratio=0.00%
  - netWeight: string; null_ratio=0.00%
  - product: string; null_ratio=0.00% [primary key]
  - productGroup: string; null_ratio=0.00%
  - productOldId: string; null_ratio=0.00%
  - productType: string; null_ratio=0.00%
  - weightUnit: string; null_ratio=0.00%
- Possible foreign keys:
  - product -> product_descriptions.product (source coverage=100.0%, overlap=69)

### Entity: sales_order_headers
- Records: 100
- Likely primary key: salesOrder
- Fields:
  - createdByUser: string; null_ratio=0.00%
  - creationDate: datetime; null_ratio=0.00%
  - customerPaymentTerms: string; null_ratio=0.00%
  - deliveryBlockReason: string; null_ratio=0.00%
  - distributionChannel: string; null_ratio=0.00%
  - headerBillingBlockReason: string; null_ratio=0.00%
  - incotermsClassification: string; null_ratio=0.00%
  - incotermsLocation1: string; null_ratio=0.00%
  - lastChangeDateTime: datetime; null_ratio=0.00%
  - organizationDivision: string; null_ratio=0.00%
  - overallDeliveryStatus: string; null_ratio=0.00%
  - overallOrdReltdBillgStatus: string; null_ratio=0.00%
  - overallSdDocReferenceStatus: string; null_ratio=0.00%
  - pricingDate: datetime; null_ratio=0.00%
  - requestedDeliveryDate: datetime; null_ratio=0.00%
  - salesGroup: string; null_ratio=0.00%
  - salesOffice: string; null_ratio=0.00%
  - salesOrder: string; null_ratio=0.00% [primary key]
  - salesOrderType: string; null_ratio=0.00%
  - salesOrganization: string; null_ratio=0.00%
  - soldToParty: string; null_ratio=0.00%
  - totalCreditCheckStatus: string; null_ratio=0.00%
  - totalNetAmount: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - soldToParty -> business_partner_addresses.businessPartner (source coverage=100.0%, overlap=8)
  - soldToParty -> business_partners.businessPartner (source coverage=100.0%, overlap=8)
  - soldToParty -> customer_company_assignments.customer (source coverage=100.0%, overlap=8)

### Entity: sales_order_items
- Records: 167
- Likely primary key: salesOrder + salesOrderItem
- Fields:
  - itemBillingBlockReason: string; null_ratio=0.00%
  - material: string; null_ratio=0.00%
  - materialGroup: string; null_ratio=0.00%
  - netAmount: string; null_ratio=0.00%
  - productionPlant: string; null_ratio=0.00%
  - requestedQuantity: string; null_ratio=0.00%
  - requestedQuantityUnit: string; null_ratio=0.00%
  - salesDocumentRjcnReason: string; null_ratio=0.00%
  - salesOrder: string; null_ratio=0.00%
  - salesOrderItem: string; null_ratio=0.00%
  - salesOrderItemCategory: string; null_ratio=0.00%
  - storageLocation: string; null_ratio=0.00%
  - transactionCurrency: string; null_ratio=0.00%
- Possible foreign keys:
  - material -> product_descriptions.product (source coverage=100.0%, overlap=69)
  - material -> products.product (source coverage=100.0%, overlap=69)
  - productionPlant -> plants.plant (source coverage=100.0%, overlap=7)
  - salesOrder -> sales_order_headers.salesOrder (source coverage=100.0%, overlap=100)

### Entity: sales_order_schedule_lines
- Records: 179
- Likely primary key: not found (likely composite or no strict PK)
- Fields:
  - confdOrderQtyByMatlAvailCheck: string; null_ratio=0.00%
  - confirmedDeliveryDate: datetime; null_ratio=6.70%
  - orderQuantityUnit: string; null_ratio=0.00%
  - salesOrder: string; null_ratio=0.00%
  - salesOrderItem: string; null_ratio=0.00%
  - scheduleLine: string; null_ratio=0.00%
- Possible foreign keys:
  - salesOrder -> sales_order_headers.salesOrder (source coverage=100.0%, overlap=100)

## Relationships

- billing_document_cancellations (1 or N) -> (1) journal_entry_items_accounts_receivable via accountingDocument = accountingDocument (coverage=80.0%)
- billing_document_cancellations (1 or N) -> (1) payments_accounts_receivable via accountingDocument = accountingDocument (coverage=80.0%)
- billing_document_cancellations (1 or N) -> (1) billing_document_headers via billingDocument = billingDocument (coverage=100.0%)
- billing_document_cancellations (N) -> (1) business_partner_addresses via soldToParty = businessPartner (coverage=100.0%)
- billing_document_cancellations (N) -> (1) business_partners via soldToParty = businessPartner (coverage=100.0%)
- billing_document_cancellations (N) -> (1) customer_company_assignments via soldToParty = customer (coverage=100.0%)
- billing_document_headers (1 or N) -> (1) journal_entry_items_accounts_receivable via accountingDocument = accountingDocument (coverage=75.5%)
- billing_document_headers (1 or N) -> (1) payments_accounts_receivable via accountingDocument = accountingDocument (coverage=73.6%)
- billing_document_headers (N) -> (1) billing_document_cancellations via cancelledBillingDocument = billingDocument (coverage=98.8%)
- billing_document_headers (N) -> (1) business_partner_addresses via soldToParty = businessPartner (coverage=100.0%)
- billing_document_headers (N) -> (1) business_partners via soldToParty = businessPartner (coverage=100.0%)
- billing_document_headers (N) -> (1) customer_company_assignments via soldToParty = customer (coverage=100.0%)
- billing_document_items (N) -> (1) billing_document_headers via billingDocument = billingDocument (coverage=100.0%)
- billing_document_items (N) -> (1) product_descriptions via material = product (coverage=100.0%)
- billing_document_items (N) -> (1) products via material = product (coverage=100.0%)
- billing_document_items (N) -> (1) outbound_delivery_headers via referenceSdDocument = deliveryDocument (coverage=100.0%)
- business_partner_addresses (1 or N) -> (1) business_partners via businessPartner = businessPartner (coverage=100.0%)
- business_partner_addresses (1 or N) -> (1) customer_company_assignments via businessPartner = customer (coverage=100.0%)
- business_partners (1 or N) -> (1) business_partner_addresses via businessPartner = businessPartner (coverage=100.0%)
- business_partners (1 or N) -> (1) customer_company_assignments via businessPartner = customer (coverage=100.0%)
- business_partners (1 or N) -> (1) business_partner_addresses via customer = businessPartner (coverage=100.0%)
- business_partners (1 or N) -> (1) customer_company_assignments via customer = customer (coverage=100.0%)
- customer_company_assignments (1 or N) -> (1) business_partner_addresses via customer = businessPartner (coverage=100.0%)
- customer_company_assignments (1 or N) -> (1) business_partners via customer = businessPartner (coverage=100.0%)
- customer_sales_area_assignments (N) -> (1) business_partner_addresses via customer = businessPartner (coverage=100.0%)
- customer_sales_area_assignments (N) -> (1) business_partners via customer = businessPartner (coverage=100.0%)
- customer_sales_area_assignments (N) -> (1) customer_company_assignments via customer = customer (coverage=100.0%)
- journal_entry_items_accounts_receivable (1 or N) -> (1) payments_accounts_receivable via accountingDocument = accountingDocument (coverage=97.6%)
- journal_entry_items_accounts_receivable (N) -> (1) payments_accounts_receivable via clearingAccountingDocument = accountingDocument (coverage=72.7%)
- journal_entry_items_accounts_receivable (N) -> (1) business_partner_addresses via customer = businessPartner (coverage=100.0%)
- journal_entry_items_accounts_receivable (N) -> (1) business_partners via customer = businessPartner (coverage=100.0%)
- journal_entry_items_accounts_receivable (N) -> (1) customer_company_assignments via customer = customer (coverage=100.0%)
- journal_entry_items_accounts_receivable (1 or N) -> (1) billing_document_headers via referenceDocument = billingDocument (coverage=100.0%)
- outbound_delivery_headers (N) -> (1) plants via shippingPoint = plant (coverage=100.0%)
- outbound_delivery_items (N) -> (1) outbound_delivery_headers via deliveryDocument = deliveryDocument (coverage=100.0%)
- outbound_delivery_items (N) -> (1) plants via plant = plant (coverage=100.0%)
- outbound_delivery_items (N) -> (1) sales_order_headers via referenceSdDocument = salesOrder (coverage=100.0%)
- payments_accounts_receivable (1 or N) -> (1) journal_entry_items_accounts_receivable via accountingDocument = accountingDocument (coverage=100.0%)
- payments_accounts_receivable (N) -> (1) journal_entry_items_accounts_receivable via clearingAccountingDocument = accountingDocument (coverage=73.7%)
- payments_accounts_receivable (N) -> (1) business_partner_addresses via customer = businessPartner (coverage=100.0%)
- payments_accounts_receivable (N) -> (1) business_partners via customer = businessPartner (coverage=100.0%)
- payments_accounts_receivable (N) -> (1) customer_company_assignments via customer = customer (coverage=100.0%)
- product_descriptions (1 or N) -> (1) products via product = product (coverage=100.0%)
- product_plants (N) -> (1) plants via plant = plant (coverage=100.0%)
- product_plants (N) -> (1) product_descriptions via product = product (coverage=100.0%)
- product_plants (N) -> (1) products via product = product (coverage=100.0%)
- product_storage_locations (N) -> (1) plants via plant = plant (coverage=100.0%)
- product_storage_locations (N) -> (1) product_descriptions via product = product (coverage=100.0%)
- product_storage_locations (N) -> (1) products via product = product (coverage=100.0%)
- products (1 or N) -> (1) product_descriptions via product = product (coverage=100.0%)
- sales_order_headers (N) -> (1) business_partner_addresses via soldToParty = businessPartner (coverage=100.0%)
- sales_order_headers (N) -> (1) business_partners via soldToParty = businessPartner (coverage=100.0%)
- sales_order_headers (N) -> (1) customer_company_assignments via soldToParty = customer (coverage=100.0%)
- sales_order_items (N) -> (1) product_descriptions via material = product (coverage=100.0%)
- sales_order_items (N) -> (1) products via material = product (coverage=100.0%)
- sales_order_items (N) -> (1) plants via productionPlant = plant (coverage=100.0%)
- sales_order_items (N) -> (1) sales_order_headers via salesOrder = salesOrder (coverage=100.0%)
- sales_order_schedule_lines (N) -> (1) sales_order_headers via salesOrder = salesOrder (coverage=100.0%)

## Business Flow

Sales Order -> Delivery -> Billing -> Payment -> Journal Entry

- Sales Order to Delivery: outbound_delivery_items.referenceSdDocument links to sales_order_headers.salesOrder; delivery header is outbound_delivery_headers.deliveryDocument.
- Delivery to Billing: billing_document_items.referenceSdDocument links to outbound_delivery_headers.deliveryDocument; billing header joins by billingDocument.
- Billing to Payment: billing_document_headers.accountingDocument links to payments_accounts_receivable.accountingDocument.
- Billing to Journal: journal_entry_items_accounts_receivable.referenceDocument links to billing_document_headers.billingDocument; accountingDocument also links to journals.

## Edge Cases

- Missing links (counts):
  - orders_without_items: 0
  - orders_without_delivery: 14
  - deliveries_without_items: 0
  - deliveries_without_billing: 3
  - billing_without_items: 0
  - billing_without_payment_by_accounting: 43
  - billing_without_journal_by_accounting: 40
- Orphan reference checks:
  - delivery_item_order_ref_orphans: 0
  - billing_item_delivery_ref_orphans: 0
  - journal_reference_billing_orphans: 0
- Potential N:N bridge entities:
  - product_plants bridges products and plants (many products per plant and many plants per product).
  - product_storage_locations bridges products, plants, and storage locations.
- Nullable fields (>20% null):
  - outbound_delivery_items.lastChangeDate: 100.0% null
  - payments_accounts_receivable.assignmentReference: 100.0% null
  - payments_accounts_receivable.costCenter: 100.0% null
  - payments_accounts_receivable.invoiceReference: 100.0% null
  - payments_accounts_receivable.invoiceReferenceFiscalYear: 100.0% null
  - payments_accounts_receivable.salesDocument: 100.0% null
  - payments_accounts_receivable.salesDocumentItem: 100.0% null
  - product_storage_locations.dateOfLastPostedCntUnRstrcdStk: 100.0% null
  - products.crossPlantStatusValidityDate: 100.0% null
  - outbound_delivery_headers.actualGoodsMovementDate: 96.5% null

## Sample Insights

### Record Counts by Entity
- billing_document_cancellations: 80
- billing_document_headers: 163
- billing_document_items: 245
- business_partner_addresses: 8
- business_partners: 8
- customer_company_assignments: 8
- customer_sales_area_assignments: 28
- journal_entry_items_accounts_receivable: 123
- outbound_delivery_headers: 86
- outbound_delivery_items: 137
- payments_accounts_receivable: 120
- plants: 44
- product_descriptions: 69
- product_plants: 3036
- product_storage_locations: 16723
- products: 69
- sales_order_headers: 100
- sales_order_items: 167
- sales_order_schedule_lines: 179

### Sample End-to-End Flows
- Flow 1: salesOrder=740509, soldToParty=320000083, salesOrg=ABCD
  - order_items=1
  - deliveries=80738040
  - billings=90504204, 91150217
  - accountingDocuments=9400000205, 9400635988
  - payment_docs=9400000205, 9400635988
  - journal_docs=9400000205, 9400635988
- Flow 2: salesOrder=740510, soldToParty=320000083, salesOrg=ABCD
  - order_items=1
  - deliveries=80738041
  - billings=90504206, 91150216
  - accountingDocuments=9400000206, 9400635987
  - payment_docs=9400000206, 9400635987
  - journal_docs=9400000206, 9400635987
- Flow 3: salesOrder=740511, soldToParty=320000083, salesOrg=ABCD
  - order_items=1
  - deliveries=80738042
  - billings=90504207, 91150215
  - accountingDocuments=9400000208, 9400635986
  - payment_docs=9400000208, 9400635986
  - journal_docs=9400000208, 9400635986

### Noted Anomalies
- Some sales orders never progressed to delivery.
- Some deliveries are not billed.
- Some billing accounting documents have no corresponding payment records.
- Some billing accounting documents have no matching journal entries by accountingDocument.

## Suggested Graph Model

### Node Types
- Order (sales_order_headers)
- OrderItem (sales_order_items)
- Delivery (outbound_delivery_headers)
- DeliveryItem (outbound_delivery_items)
- Invoice (billing_document_headers)
- InvoiceItem (billing_document_items)
- Payment (payments_accounts_receivable)
- JournalEntryAR (journal_entry_items_accounts_receivable)
- Customer (business_partners)
- CustomerAddress (business_partner_addresses)
- Product (products)
- Plant (plants)
- ProductPlant (product_plants)
- ProductStorageLocation (product_storage_locations)

### Edge Types
- Order -[HAS_ITEM]-> OrderItem via salesOrder
- Order -[ORDERED_BY]-> Customer via soldToParty -> businessPartner
- DeliveryItem -[DELIVERS_ORDER]-> Order via referenceSdDocument -> salesOrder
- Delivery -[HAS_ITEM]-> DeliveryItem via deliveryDocument
- InvoiceItem -[BILLS_DELIVERY]-> Delivery via referenceSdDocument -> deliveryDocument
- Invoice -[HAS_ITEM]-> InvoiceItem via billingDocument
- Invoice -[POSTED_TO]-> Payment via accountingDocument
- Invoice -[POSTED_TO]-> JournalEntryAR via accountingDocument
- JournalEntryAR -[REFERENCES_INVOICE]-> Invoice via referenceDocument -> billingDocument
- OrderItem -[FOR_PRODUCT]-> Product via material -> product
- DeliveryItem -[FROM_PLANT]-> Plant via plant
- ProductPlant -[LINKS_PRODUCT]-> Product via product
- ProductPlant -[LINKS_PLANT]-> Plant via plant
- ProductStorageLocation -[STORES_PRODUCT]-> Product via product
- ProductStorageLocation -[AT_PLANT]-> Plant via plant

### Implementation Notes
- Use stable business keys from source systems (e.g., salesOrder, deliveryDocument, billingDocument, accountingDocument) as node IDs.
- Keep item entities as first-class nodes to preserve 1:N semantics and avoid property-array anti-patterns.
- Persist relationship confidence/coverage metadata for inferred edges when strict FK constraints are absent.