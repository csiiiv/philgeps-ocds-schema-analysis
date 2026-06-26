# PhilGEPS OCDS ↔ CSV field crosswalk

Side-by-side reference: **OCDS field** → **PhilGEPS 1.5** → **PhilGEPS 2.0** → **V2 CSV** → **V1 CSV** → **Canonical** (all open-data schemas → canonical field).

> **Canonical column** uses compact schema keys: **S1** (2000–2015 XLSX), **S2** (2016–2020 XLSX), **S3** (2021–2024 CSV), **S4** (2025 CSV), **S5** (2021–2024-V2 CSV). Full per-schema dictionary: [`PHILGEPS_CANONICAL_FIELD_MAP.json`](PHILGEPS_CANONICAL_FIELD_MAP.json).

| OCDS field | PhilGEPS 1.5 field | PhilGEPS 2.0 field | V2 CSV column | V1 CSV column | Canonical |
|---|---|---|---|---|---|
| `awards/contractPeriod/endDate` | `M_Award (AwardID)` | `Notice to Proceed (Contract End Date)` | Award Reference No. | Award No. | S1–S5: Contract End Date → contract_end_date |
| `awards/contractPeriod/startDate` | `D_AwardAwardee (ContractStartDate)` | `Notice to Proceed (Contract Effectivity Date)` | Contract Effectivity Date | Contract Efectivity Date | S1–S3: Contract Efectivity Date · S4–S5: Contract Effectivity Date → contract_effectivity_date |
| `awards/date` | `M_Award (PublishDate)` | `Awards (Award Date)` | Published Date(Award) | Published Date(Award) | S1–S5: Award Date → award_date |
| `awards/description` | `D_AwardDetail (Description)` | `—` | Item Description | Item Description | S1–S5: Item Description → item_description (line-item scope) |
| `awards/documents/dateModified` | `M_Award (ModifiedDate)` | `Awards Documents (Modified date)` | — | — | omit (documents not in open CSV) |
| `awards/documents/datePublished` | `M_Award (PublishDate)` | `Awards Documents (Created date)` | Published Date(Award) | Published Date(Award) | omit (documents not in open CSV) |
| `awards/documents/description` | `R3_File (FileName)` | `—` | — | — | omit |
| `awards/documents/id` | `R3_File (FileID)` | `Awards Documents (ID)` | — | — | omit |
| `awards/id` | `M_Award (AwardID)` | `Awards (ID)` | Award Reference No. | Award No. | S1–S3: Award No. · S4–S5: Award Reference No. → award_reference_no |
| `awards/items/description` | `D_AwardDetail (Description)` | `Awards Item (Item Description)` | Item Description | Item Description | S1–S2: Item Desc · S3–S5: Item Description → item_description |
| `awards/items/id` | `M_Award (AwardID)` | `Awards Item (ID)` | Award Reference No. | Award No. | S1–S3: Award No. · S4–S5: Award Reference No. → award_reference_no (award-level id; use line_item_no for item rows) |
| `awards/items/unit/name` | `M_UOM (Description)` | `—` | UOM | UOM | S1: UOM · S2: Unit of Measurement · S3–S5: UOM → uom |
| `awards/items/unit/value/amount` | `D_Tender_Item (Budget)` | `Awards Item (Unit Price)` | Item Budget | Item Budget | S1–S5: Item Budget → item_budget |
| `awards/status` | `M_Award (AwardStatus)` | `Awards (Status)` | Award Notice Status | Award Status | S1–S3: Award Status · S4–S5: Award Notice Status → award_notice_status [codelist map] |
| `awards/suppliers/id` | `D_AwardAwardee (AwardeeID)` | `Supplier (Supplier ID)` | — | — | derived: slug(awardee_organization_name) |
| `awards/suppliers/name` | `D_AwardAwardee (Awardee)` | `Awards (Awardee), Supplier (Supplier Organization Name)` | Awardee Organization Name | Awardee Organization Name | S1–S2: Awardee Corporate Title · S3–S5: Awardee Organization Name → awardee_organization_name |
| `awards/title` | `M_Award (AwardTitle)` | `Awards (Title)` | Award Title | Award Title | S1–S5: Award Title → award_title |
| `awards/value/amount` | `D_AwardAwardee (ContractAmt)` | `Awards (Contract Amount)` | Contract Amount | Contract Amount | S1–S5: Contract Amount → contract_amount |
| `buyer/id` | `M_Organization (OrgID)` | `departments_government_agency (UACS_code)` | — | — | derived: slug(procuring_entity) |
| `buyer/name` | `M_Organization (OrgName)` | `departments_government_agency (name), Tenders (Agency Name)` | Procuring Entity (PE) | Procuring Entity | S1–S2: Organization Name · S3: Procuring Entity · S4–S5: Procuring Entity (PE) → procuring_entity |
| `contracts/awardID` | `M_Award (AwardID)` | `Notice to Proceed (Award ID)` | Award Reference No. | Award No. | S1–S3: Award No. · S4–S5: Award Reference No. → award_reference_no |
| `contracts/dateSigned` | `D_AwardAwardee (AwardDate)` | `Awards (Award Date)` | Award Date | Award Date | S1–S5: Award Date → award_date |
| `contracts/description` | `D_AwardDetail (Description)` | `—` | Item Description | Item Description | S1–S2: Item Desc · S3–S5: Item Description → item_description |
| `contracts/documents/dateModified` | `M_Award (ModifiedDate)` | `—` | — | — | omit |
| `contracts/documents/datePublished` | `M_Award (PublishDate)` | `—` | Published Date(Award) | Published Date(Award) | omit |
| `contracts/documents/id` | `R4_AwardNotice_AwardDoc (ANAwardDocID)` | `Contract Management Documents (ID)` | — | — | omit |
| `contracts/documents/title` | `R3_File (Name)` | `Contract Management Documents (Name)` | — | — | omit |
| `contracts/implementation/transactions/payee/id` | `D_AwardAwardee (AwardeeID)` | `Supplier (Supplier ID)` | — | — | derived: slug(awardee_organization_name) |
| `contracts/implementation/transactions/payee/name` | `D_AwardAwardee (Awardee)` | `Supplier (Supplier Organization Name)` | Awardee Organization Name | Awardee Organization Name | S1–S2: Awardee Corporate Title · S3–S5: Awardee Organization Name → awardee_organization_name |
| `contracts/implementation/transactions/payer/id` | `M_Tender (ProcuringEntityOrgID)` | `Tenders (Agency ID (Foreign Key))` | — | — | derived: slug(procuring_entity) |
| `contracts/implementation/transactions/payer/name` | `M_Tender (ProcuringEntityOrg)` | `Tenders (Agency Name)` | Procuring Entity (PE) | Procuring Entity | S1–S2: Organization Name · S3: Procuring Entity · S4–S5: Procuring Entity (PE) → procuring_entity |
| `contracts/items/description` | `D_AwardDetail (ItemName)` | `Awards Item (Item Description)` | Item Name | Item Name | S1–S5: Item Name → item_name |
| `contracts/items/id` | `D_AwardDetail (LineItemID)` | `Awards Item (ID)` | — | — | S1–S5: Line Item No → line_item_no |
| `contracts/items/quantity` | `D_AwardDetail (Qty)` | `Awards Item (Quantity)` | Quantity | Quantity | S1–S5: Quantity → quantity |
| `contracts/items/unit/value/amount` | `D_AwardDetail (Budget)` | `—` | Item Budget | Item Budget | S1–S5: Item Budget → item_budget |
| `contracts/period/endDate` | `D_AwardAwardee (ContractEndDate)` | `Notice to Proceed (Contract End Date)` | Contract End Date | Contract End Date | S1–S5: Contract End Date → contract_end_date |
| `contracts/period/startDate` | `D_AwardAwardee (ContractStartDate)` | `Notice to Proceed (Contract Effectivity Date)` | Contract Effectivity Date | Contract Efectivity Date | S1–S3: Contract Efectivity Date · S4–S5: Contract Effectivity Date → contract_effectivity_date |
| `contracts/status` | `M_Award (AwardStatus)` | `Notice to Proceed (Contract Status)` | Award Notice Status | Award Status | S1–S3: Award Status · S4–S5: Award Notice Status → award_notice_status [codelist map] |
| `contracts/title` | `M_Award (AwardTitle)` | `Notice to Proceed (Contract Title)` | Award Title | Award Title | S1–S5: Award Title → award_title |
| `contracts/value/amount` | `D_AwardAwardee (ContractAmt)` | `Notice to Proceed (Contract Amount)` | Contract Amount | Contract Amount | S1–S5: Contract Amount → contract_amount |
| `parties/address/countryName` | `M_Country (CountryName)` | `Supplier (Country)` | Country of Awardee | — | S4–S5: Country of Awardee → awardee_country |
| `parties/address/locality` | `M_Province (ProvinceName)` | `departments_government_agency (province), Supplier (Province)` | Province, Province of Awardee | — | S4–S5: Province → pe_province · S4–S5: Province of Awardee → awardee_province |
| `parties/address/postalCode` | `M_Organization (ZipCode)` | `departments_government_agency (zip_code), Supplier (Zip Code)` | — | — | omit |
| `parties/address/region` | `M_Region (RegionName)` | `departments_government_agency (region), Supplier (Region)` | Region, Region of Awardee | — | S4–S5: Region → pe_region · S4–S5: Region of Awardee → awardee_region |
| `parties/address/streetAddress` | `D_AwardAwardee (Address)` | `departments_government_agency (street_address), Supplier (Address)` | — | — | omit |
| `parties/address/streetAddress` | `M_Organization (Address1)` | `departments_government_agency (street_address), Supplier (Address)` | — | — | omit |
| `parties/contactPoint/email` | `M_User (Email)` | `Buyer (Email), Supplier_User (Email)` | — | — | omit (privacy / not in CSV) |
| `parties/contactPoint/faxNumber` | `M_User (FaxAreaCode + FaxNo)` | `—` | — | — | omit |
| `parties/contactPoint/name` | `D_AwardAwardee (ContactPerson)` | `Buyer (Full Name), Supplier_User (Name)` | — | Awardee Contact Person | omit (privacy excluded; S3 had Created By / Awardee Contact Person) |
| `parties/contactPoint/name` | `M_Tender (ContactPersonName)` | `Buyer (Full Name), Supplier_User (Name)` | — | Created By | omit (privacy excluded; S3 had Created By / Awardee Contact Person) |
| `parties/contactPoint/name` | `M_User (Firstname + Middlename + Lastname)` | `Buyer (Full Name), Supplier_User (Name)` | — | — | omit (privacy excluded; S3 had Created By / Awardee Contact Person) |
| `parties/contactPoint/telephone` | `M_User (TelAreaCode + TelNo + TelExtNo)` | `Buyer (Phone)` | — | — | omit |
| `parties/contactPoint/url` | `M_Organization (Website)` | `Supplier (Website)` | — | — | omit |
| `parties/details` | `M_BuyerOrgType (Description)` | `agency_organization_types (name)` | PE Organization Type, PE Organization Type (Grouped) | — | S4–S5: PE Organization Type → pe_organization_type |
| `parties/id` | `D_AwardAwardee (AwardeeID)` | `departments_government_agency (department_id), Supplier (Supplier ID), Vendors (Vendors ID)` | — | — | derived: slug(awardee_organization_name) |
| `parties/id` | `M_Organization (OrgID)` | `departments_government_agency (department_id), Supplier (Supplier ID), Vendors (Vendors ID)` | — | — | derived: slug(procuring_entity) |
| `parties/id` | `M_Tender (ProcuringEntityOrgID)` | `departments_government_agency (department_id), Supplier (Supplier ID), Vendors (Vendors ID)` | — | — | derived: slug(procuring_entity) |
| `parties/id` | `M_TenderBiddersList (OrgID)` | `departments_government_agency (department_id), Supplier (Supplier ID), Vendors (Vendors ID)` | — | — | derived: slug(parsed bidder name) |
| `parties/identifier/id` | `M_Organization (OrgID)` | `departments_government_agency (UACS_code)` | — | — | derived: slug(procuring_entity) |
| `parties/identifier/legalName` | `M_Organization (OrgName)` | `departments_government_agency (name)` | Procuring Entity (PE) | Procuring Entity | S1–S2: Organization Name · S3: Procuring Entity · S4–S5: Procuring Entity (PE) → procuring_entity |
| `parties/name` | `D_AwardAwardee (Awardee)` | `departments_government_agency (name), Supplier (Supplier Organization Name), Vendors (Name)` | Awardee Organization Name | Awardee Organization Name | V2/V1: Awardee Organization Name → awardee_organization_name |
| `parties/name` | `M_Organization (OrgName)` | `departments_government_agency (name), Supplier (Supplier Organization Name), Vendors (Name)` | Procuring Entity (PE) | Procuring Entity | V2: Procuring Entity (PE) \| V1: Procuring Entity → procuring_entity |
| `parties/name` | `M_Tender (ProcuringEntityOrg)` | `departments_government_agency (name), Supplier (Supplier Organization Name), Vendors (Name)` | Procuring Entity (PE) | Procuring Entity | V2: Procuring Entity (PE) \| V1: Procuring Entity → procuring_entity |
| `parties/name` | `M_TenderBiddersList (OrgName)` | `departments_government_agency (name), Supplier (Supplier Organization Name), Vendors (Name)` | — | List of Bidder's | V1: List of Bidder's → bidders [parse ; only] |
| `parties/roles` | `M_Role (RoleName)` | `Buyer (User Role ID)` | — | — | omit |
| `planning/budget/amount/amount` | `M_Tender (ApprovedBudget)` | `app_line_items (Total Estimated Budget), Tenders Items (Estimated Budget Cost)` | Approved Budget of the Contract | Approved Budget of the Contract | S1–S5: Approved Budget of the Contract → approved_budget |
| `planning/budget/description` | `M_Tender (Funding Source)` | `APP Details (Source of Funds), PR (Funding Source)` | Funding Source | Funding Source | S1–S5: Funding Source → funding_source |
| `planning/budget/project` | `M_Tender (TenderTitle)` | `APP Details (Procurement Program/Project Title), PR (Project Name)` | Notice Title | Notice Title | S1–S5: Notice Title → notice_title |
| `relatedProcesses/id` | `M_Tender (RefNo)` | `Tenders (Tender ID)` | Bid Reference No. | Bid Reference No. | S1–S2: Reference ID · S3–S5: Bid Reference No. → bid_reference_no (S3 fallback: Solicitation No. if 0) |
| `relatedProcesses/relationship` | `M_Tender (ProcuringEntityOrg)` | `Tenders (Agency Name)` | Procuring Entity (PE) | Procuring Entity | constant: parent |
| `relatedProcesses/title` | `M_Tender (TenderTitle)` | `Tenders (Tender Title)` | Notice Title | Notice Title | S1–S5: Notice Title → notice_title |
| `tender/additionalProcurementCategories` | `M_Tender (BusCat)` | `Tenders Items (Business Category)` | Business Category | Business Category | S1–S5: Business Category → business_category |
| `tender/amendments/date` | `M_BidSupplement (CreationDate)` | `Tender_Supplement (Created Date)` | — | — | omit |
| `tender/amendments/description` | `M_BidSupplement (Description)` | `Tender_Supplement (Description)` | — | — | omit |
| `tender/amendments/id` | `M_BidSupplement (BidSuppID)` | `Tender_Supplement (ID)` | — | — | omit |
| `tender/amendments/rationale` | `M_BidSupplement (BidSuppTitle)` | `Tender_Supplement (Name)` | — | — | omit |
| `tender/awardCriteriaDetails` | `D_AwardAwardee (AwardReason)` | `—` | — | Reason for Award | S1–S3: Reason for Award → reason_for_award [extension] |
| `tender/awardPeriod/durationInDays` | `M_Tender (ContractDuration + CalendarType)` | `Tenders (Contract Period)` | Contract Duration, Calendar Type | Contract Duration, Calendar Type | derive: S1–S5 Contract Duration + Calendar Type → contract_duration |
| `tender/awardPeriod/startDate` | `M_Award (PublishDate)` | `Awards (Award Date)` | Published Date(Award) | Published Date(Award) | S1–S2: Publish Date(Award) · S3–S5: Published Date(Award) → award_published_date |
| `tender/contractPeriod/endDate` | `D_AwardAwardee (ContractEndDate)` | `Notice to Proceed (Contract End Date)` | Contract End Date | Contract End Date | S1–S5: Contract End Date → contract_end_date |
| `tender/contractPeriod/startDate` | `D_AwardAwardee (ContractStartDate)` | `Notice to Proceed (Contract Effectivity Date)` | Contract Effectivity Date | Contract Efectivity Date | S1–S3: Contract Efectivity Date · S4–S5: Contract Effectivity Date → contract_effectivity_date |
| `tender/description` | `M_Tender (Description)` | `Tenders (Description)` | — | — | omit (use notice_title or item_description) |
| `tender/documents/dateModified` | `M_Document (ModifiedDate)` | `Tender Documents (Modified date)` | — | — | omit |
| `tender/documents/datePublished` | `M_Document (AcceptedDate)` | `Tender Documents (Publish date)` | — | — | omit |
| `tender/documents/documentType` | `M_Document (Content)` | `—` | — | — | omit |
| `tender/documents/format` | `M_Document (Format)` | `—` | — | — | omit |
| `tender/documents/id` | `M_Document (DocID)` | `Tender Documents (ID)` | — | — | omit |
| `tender/documents/title` | `M_Document (DocName)` | `Tender Documents (Title)` | — | — | omit |
| `tender/enquiryPeriod/endDate` | `M_Tender (ClosingDate)` | `Tenders (Tender End Datetime)` | Closing Date | Closing Date | S1–S5: Closing Date → closing_date |
| `tender/enquiryPeriod/startDate` | `M_Tender (PublishDate)` | `Tenders (Tender Start Datetime)` | Published Date | Published Date | S1–S2: Publish Date · S3–S5: Published Date → published_date |
| `tender/id` | `M_Tender (RefNo)` | `Tenders (Tender ID)` | Bid Reference No. | Bid Reference No. | S1–S2: Reference ID · S3–S5: Bid Reference No. → bid_reference_no |
| `tender/items/additionalClassifications/description` | `M_UNSPSC (Description)` | `Tenders Items (UNSPSC Description)` | UNSPSC Description | UNSPSC Description | S1–S5: UNSPSC Description → unspsc_description |
| `tender/items/additionalClassifications/id` | `M_UNSPSC (UNSPSCCode)` | `Tenders Items (UNSPSC Code)` | UNSPSC Code | UNSPSC Code | S1–S5: UNSPSC Code → unspsc_code |
| `tender/items/additionalClassifications/scheme` | `M_UNSPSC (UNSPSCCode)` | `Tenders Items (UNSPSC Code)` | UNSPSC Code | UNSPSC Code | constant: UNSPSC |
| `tender/items/classification/description` | `M_Classification (Description)` | `Tenders (Classification)` | Classification | Classification | S1–S5: Classification → classification [codelist map] |
| `tender/items/classification/id` | `M_Tender (ClassificationID)` | `Tenders (Classification ID)` | — | — | omit |
| `tender/items/description` | `D_Tender_Item (ItemName)` | `Tenders Items (Item Description)` | Item Name | Item Name | S1–S2: Item Desc · S3–S5: Item Description → item_description |
| `tender/items/id` | `D_Tender_Item (LineItemID)` | `Tenders Items (Item ID)` | Line Item No | Line Item No | S1–S5: Line Item No → line_item_no |
| `tender/items/unit/id` | `M_UOM (UMOID)` | `Unit of Measure (ID)` | — | — | omit |
| `tender/items/unit/name` | `M_UOM (Description)` | `Unit of Measure (Unit of Measure)` | UOM | UOM | S1: UOM · S2: Unit of Measurement · S3–S5: UOM → uom |
| `tender/items/unit/value/amount` | `D_Tender_Item (Budget)` | `Tenders Items (Estimated Budget Cost), Item Details (Product Price)` | Item Budget | Item Budget | S1–S5: Item Budget → item_budget |
| `tender/mainProcurementCategory` | `M_Tender (Classification)` | `Tenders (Classification)` | Classification | Classification | S1–S5: Classification → classification [codelist map] |
| `tender/milestones/code` | `M_Tender (PreBidDate)` | `Tenders (prebid_meeting_start_datetime)` | — | PreBid Date | S1–S3: PreBid Date → prebid_date [milestone:preBid] |
| `tender/milestones/dateMet` | `M_Tender (PreBidDate)` | `Tenders (prebid_meeting_end_datetime)` | — | PreBid Date | S1–S3: PreBid Date → prebid_date |
| `tender/procurementMethod` | `M_Tender (ProcurementMode)` | `Tenders (Procurement Mode)` | Procurement Mode | Procurement Mode | S1–S5: Procurement Mode → procurement_mode [codelist map] |
| `tender/procuringEntity/id` | `M_Tender (ProcuringEntityOrgID)` | `Tenders (Agency ID (Foreign Key))` | — | — | derived: slug(procuring_entity) |
| `tender/procuringEntity/name` | `M_Tender (ProcuringEntityOrg)` | `Tenders (Agency Name)` | Procuring Entity (PE) | Procuring Entity | S1–S2: Organization Name · S3: Procuring Entity · S4–S5: Procuring Entity (PE) → procuring_entity |
| `tender/status` | `M_Tender (TenderStatus)` | `Tenders (Status)` | Bid Notice Status | Notice Status | S1–S3: Notice Status · S4–S5: Bid Notice Status → bid_notice_status [codelist map] |
| `tender/tenderPeriod/endDate` | `M_Tender (ClosingDate)` | `Tenders (Tender End Datetime)` | Closing Date | Closing Date | S1–S5: Closing Date → closing_date |
| `tender/tenderPeriod/startDate` | `M_Tender (PublishDate)` | `Tenders (Tender Start Datetime)` | Published Date | Published Date | S1–S2: Publish Date · S3–S5: Published Date → published_date |
| `tender/tenderers/id` | `M_TenderBiddersList (OrgID)` | `Tender_Participants (Vendor ID)` | — | — | derived: slug(parsed bidder name) |
| `tender/tenderers/name` | `M_TenderBiddersList (OrgName)` | `Vendors (Name), Tender_Participants (Vendor Name)` | — | List of Bidder's | S3: List of Bidder's → bidders [parse ; html-unescape] |
| `tender/value/amount` | `M_Tender (ApprovedBudget)` | `Tenders Items (Estimated Budget Cost)` | Approved Budget of the Contract | Approved Budget of the Contract | S1–S5: Approved Budget of the Contract → approved_budget |
| `—` | `D_AwardAwardee (AwardType) *(unmapped)*` | `—` | — | Award Type | S1–S3: Award Type → award_type [extension] |
| `—` | `D_AwardAwardee (ContractNo) *(unmapped)*` | `—` | — | Contract No | S1–S3: Contract No → contract_no [extension] |
| `—` | `D_AwardAwardee (Proceed Date) *(unmapped)*` | `—` | Notice to Proceed Date | Notice to Proceed Date | S1–S5: Notice to Proceed Date → notice_to_proceed_date [extension] |
| `—` | `D_Tender_Item (ItemDesc) *(unmapped)*` | `—` | Item Description | Item Description | S1–S2: Item Desc · S3–S5: Item Description → item_description |
| `—` | `D_Tender_Item (Qty) *(unmapped)*` | `—` | Quantity | Quantity | S1–S5: Quantity → quantity |
| `—` | `D_Tender_Item (UOM) *(unmapped)*` | `—` | UOM | UOM | S1: UOM · S2: Unit of Measurement · S3–S5: UOM → uom |
| `—` | `M_Tender (Funding Instrument) *(unmapped)*` | `—` | Funding Instrument | Funding Instrument | S1–S5: Funding Instrument → funding_instrument [extension] |
| `—` | `M_Tender (NoticeType) *(unmapped)*` | `—` | — | Notice Type | S1–S3: Notice Type → notice_type [extension] |
| `—` | `M_Tender (SolicitationNo) *(unmapped)*` | `—` | — | Solicitation No. | S1–S3: Solicitation No. → solicitation_no [extension] |
| `—` | `M_Tender (TradeAgreement) *(unmapped)*` | `—` | Trade Agreement | Trade Agreement | S1–S5: Trade Agreement → trade_agreement [extension] |
| `—` | `—` | `APP (ID)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `APP Details (Annual Year)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Auditor (Name)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Award_Participants (Vendor Name)` | Awardee Joint Venture | — | S4–S5: Awardee Joint Venture → awardee_joint_venture [parse ;] |
| `—` | `—` | `Awards (Reason of Award)` | — | Reason for Award | S1–S3: Reason for Award → reason_for_award [extension] |
| `—` | `—` | `Awards (Vendor Acceptance Date)` | Notice to Proceed Date | — | S4–S5: Notice to Proceed Date → notice_to_proceed_date [extension] |
| `—` | `—` | `CSO (Organization Name)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Contract Payment Details (Contract Amount)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `PO GRN (Number of Days)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `PO Milestones (Name)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `PR (PR Date)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `PR (PR Number)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Purchase Orders (Vendor Name)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Supplier (City)` | City/Municipality of Awardee | — | S4–S5: City/Municipality of Awardee → awardee_city_municipality |
| `—` | `—` | `Supplier (Company Type)` | Awardee Size | — | S4–S5: Awardee Size → awardee_size |
| `—` | `—` | `Supplier (SEC Registration Number)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Supplier (Tax Number)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Tender_BAC (Member Name)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `Tenders (Delivery Location)` | Area of Delivery | Area of Delivery | S1–S5: Area of Delivery → area_of_delivery [extension] |
| `—` | `—` | `Tenders Items (Item Name)` | Item Name | Item Name | S1–S5: Item Name → item_name |
| `—` | `—` | `Tenders Items (Quantity)` | Quantity | Quantity | S1–S5: Quantity → quantity |
| `—` | `—` | `agency_organization_types (grouped_name)` | PE Organization Type (Grouped) | — | S4–S5: PE Organization Type (Grouped) → pe_organization_type_grouped |
| `—` | `—` | `app_line_items (Total Estimated Budget)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `app_status_tracker (Status)` | — | — | omit (PhilGEPS 2.0 internal — not in flat open CSV) |
| `—` | `—` | `departments_government_agency (city_municipality)` | City/Municipality | — | S4–S5: City/Municipality → pe_city_municipality |
| `—` | `—` | `departments_government_agency (city_name)` | City/Municipality | — | S4–S5: City/Municipality → pe_city_municipality |
| `—` | `—` | `departments_government_agency (government_branch)` | Government Branch | — | S4–S5: Government Branch → pe_government_branch |
| `—` | `—` | `government_branchs (name)` | Government Branch | — | S4–S5: Government Branch → pe_government_branch |
## Legend

| Term | Source |
|---|---|
| **OCDS field** | PS-DBM v0.91 template `mapping_details` |
| **PhilGEPS 1.5** | `philgeps-1.5.json` — legacy notice/award tables |
| **PhilGEPS 2.0** | `mphilgeps.json` — modernized system (`Tenders`, `APP`, `PR`, `Supplier`, etc.) |
| **V2 CSV** | Schema 4/5 — `raw/PHILGEPS -- 2021 - 2025 (CSV) V2/` (46 cols) |
| **V1 CSV** | Schema 3 — `raw/PHILGEPS -- 2021-2025 (CSV)/` (43 cols) |
| **Canonical** | All open schemas S1–S5 → canonical field; see `PHILGEPS_CANONICAL_FIELD_MAP.json` and `config/schema_mappings.yaml` |
| **S1–S5** | Schema periods from `PHILGEPS_SCHEMA_ANALYSIS.json` (includes 2000–2020 XLSX, not only V1/V2 CSV) |

PhilGEPS 2.0 column uses **semantic** links (curated from `mphilgeps.json` table/field names and PS-DBM docs), not raw template column offsets — the shipped `mphilgeps.json` has known column-shift artefacts in `mapping_details`.

`—` = not present. `*(unmapped)*` = PhilGEPS 1.5 template field not marked mapped. `[extension]` = emit via `philgeps_extension` block in `canonical_to_ocds.yaml`. `[codelist map]` = map through `config/ocds_codelist_mappings.yaml`.

Regenerate this file and the JSON dictionary:

```bash
python scripts/build_schema_field_map.py
```

## Summary

- **151** total rows (113 with OCDS path).
- **104** rows with a suggested open-data mapping in Canonical.
- **47** rows marked omit (not in flat open CSV or privacy-excluded).
- **11** rows using derived/slug identifiers.
- Canonical prefers **S4–S5** (V2) when available, then **S3** (V1), then **S1–S2** (XLSX); PhilGEPS 2.0-only internal fields (APP, PR, PO) require WSF export or API access.
