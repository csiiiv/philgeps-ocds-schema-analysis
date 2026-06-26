# PhilGEPS Schema Evolution Analysis

**Source:** [Schema.tsx](https://raw.githubusercontent.com/csiiiv/philgeps-awards-dashboard/refs/heads/main/frontend/src/pages/About/Schema.tsx)  
**Analysis Date:** November 14, 2025  
**Purpose:** Comprehensive understanding of PhilGEPS data structure changes from 2000-2025

PhilGEPS data has evolved through **5 distinct schemas** over 25 years, reflecting the modernization of the Philippine government procurement system.

---

## Quick Reference

| Schema | Period | Format | Columns | Key Change |
|--------|--------|--------|---------|------------|
| Schema 1 | 2000-2015 | XLSX (row 3) | 40 | Original system, uses `UOM` |
| Schema 2 | 2016-2020 | XLSX (row 3) | 40 | Renamed `UOM` → `Unit of Measurement` |
| Schema 3 | 2021-2024 | CSV (row 0) | 43 | Added 3 fields: Created By, Contact Person, Bidder List |
| Schema 4 | 2025 | CSV (row 0) | 46 | Added 12 location fields, removed 9 legacy fields |
| Schema 5 | 2021-2024-V2 | CSV (row 0) | 46 | **Same as Schema 4** — Early PhilGEPS 2.0 implementation |

---

## Complete Semantic Grouping Table

Groups related fields across schemas to show how specific data categories evolved.

### PROCURING ENTITY

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Entity name | `Organization Name` | `Procuring Entity` | `Procuring Entity (PE)` | Renamed 2021, clarified 2025 |
| Region | — | — | `Region` | **NEW 2025/V2** |
| Province | — | — | `Province` | **NEW 2025/V2** |
| City/Municipality | — | — | `City/Municipality` | **NEW 2025/V2** |
| Government branch | — | — | `Government Branch` | **NEW 2025/V2** |
| Organization type | — | — | `PE Organization Type` | **NEW 2025/V2** |
| Organization type (grouped) | — | — | `PE Organization Type (Grouped)` | **NEW 2025/V2** |

### BID IDENTIFICATION

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Reference number | `Reference ID` | `Bid Reference No.` | `Bid Reference No.` | Renamed 2021 |
| Solicitation number | `Solicitation No.` | `Solicitation No.` | **REMOVED** | Legacy field dropped 2025 |
| Notice title | `Notice Title` | `Notice Title` | `Notice Title` | Stable |
| Classification | `Classification` | `Classification` | `Classification` | Stable |
| Notice type | `Notice Type` | `Notice Type` | **REMOVED** | Redundant, dropped 2025 |
| Business category | `Business Category` | `Business Category` | `Business Category` | Stable |

### BUDGET & FUNDING

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Funding source | `Funding Source` | `Funding Source` | `Funding Source` | Stable |
| Funding instrument | `Funding Instrument` | `Funding Instrument` | `Funding Instrument` | Stable |
| Approved budget | `Approved Budget of the Contract` | `Approved Budget of the Contract` | `Approved Budget of the Contract` | Stable |
| Trade agreement | `Trade Agreement` | `Trade Agreement` | `Trade Agreement` | Stable |

### BID TIMELINE

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Published date | `Publish Date` | `Published Date` | `Published Date` | Renamed 2021 |
| Pre-bid date | `PreBid Date` | `PreBid Date` | **REMOVED** | Less common, dropped 2025 |
| Closing date | `Closing Date` | `Closing Date` | `Closing Date` | Stable |

### PROCUREMENT

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Procurement mode | `Procurement Mode` | `Procurement Mode` | `Procurement Mode` | Stable |
| Area of delivery | `Area of Delivery` | `Area of Delivery` | `Area of Delivery` | Stable |
| Contract duration | `Contract Duration` | `Contract Duration` | `Contract Duration` | Stable |
| Calendar type | `Calendar Type` | `Calendar Type` | `Calendar Type` | Stable |

### LINE ITEMS

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Line item number | `Line Item No` | `Line Item No` | `Line Item No` | Stable |
| Item name | `Item Name` | `Item Name` | `Item Name` | Stable |
| Item description | `Item Desc` | `Item Description` | `Item Description` | Full word 2021 |
| Quantity | `Quantity` | `Quantity` | `Quantity` | Stable |
| Unit of measure | `UOM` (2000-2015) / `Unit of Measurement` (2016-2020) | `UOM` | `UOM` | **Changed 2016**, reverted 2021 |
| Item budget | `Item Budget` | `Item Budget` | `Item Budget` | Stable |

### UNSPSC

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| UNSPSC code | `UNSPSC Code` | `UNSPSC Code` | `UNSPSC Code` | Stable |
| UNSPSC description | `UNSPSC Description` | `UNSPSC Description` | `UNSPSC Description` | Stable |

### BID STATUS

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Bid/notice status | `Notice Status` | `Notice Status` | `Bid Notice Status` | More descriptive 2025 |
| Created by user | — | `Created By` | **REMOVED** | Added 2021, privacy concern 2025 |

### AWARD ID

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Award reference | `Award No.` | `Award No.` | `Award Reference No.` | More descriptive 2025 |
| Award title | `Award Title` | `Award Title` | `Award Title` | Stable |
| Award type | `Award Type` | `Award Type` | **REMOVED** | Simplified 2025 |

### AWARD TIMELINE

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Published date (award) | `Publish Date(Award)` | `Published Date(Award)` | `Published Date(Award)` | Renamed 2021 |
| Award date | `Award Date` | `Award Date` | `Award Date` | Stable |
| Notice to proceed | `Notice to Proceed Date` | `Notice to Proceed Date` | `Notice to Proceed Date` | Stable |
| Contract effectivity | `Contract Efectivity Date` ⚠️ | `Contract Efectivity Date` ⚠️ | `Contract Effectivity Date` ✅ | Typo fixed 2025 |
| Contract end date | `Contract End Date` | `Contract End Date` | `Contract End Date` | Stable |

### CONTRACT

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Contract amount | `Contract Amount` | `Contract Amount` | `Contract Amount` | Stable |
| Contract number | `Contract No` | `Contract No` | **REMOVED** | Auto-generated 2025 |

### AWARD STATUS

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Award status | `Award Status` | `Award Status` | `Award Notice Status` | Consistent naming 2025 |
| Reason for award | `Reason for Award` | `Reason for Award` | **REMOVED** | Simplified 2025 |

### AWARDEE INFORMATION

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| Organization name | `Awardee Corporate Title` | `Awardee Organization Name` | `Awardee Organization Name` | Renamed in 2021 |
| Contact person | — | `Awardee Contact Person` ⭐ | **REMOVED** | Added 2021, removed 2025 (privacy) |
| Country | — | — | `Country of Awardee` | **NEW in 2025/V2** |
| Region | — | — | `Region of Awardee` | **NEW in 2025/V2** |
| Province | — | — | `Province of Awardee` | **NEW in 2025/V2** |
| City/Municipality | — | — | `City/Municipality of Awardee` | **NEW in 2025/V2** |
| Awardee size | — | — | `Awardee Size` | **NEW in 2025/V2** (Small/Med/Large) |
| Joint venture | — | — | `Awardee Joint Venture` | **NEW in 2025/V2** (JV partners) |

### COMPETITION

| Field Name | Schema 1-2 (2000-2020) | Schema 3 (2021-2024) | Schema 4-5 (2025/V2) | Evolution Notes |
|------------|------------------------|----------------------|----------------------|-----------------|
| List of bidders | — | `List of Bidder's` | **REMOVED** | Added 2021, sensitive data 2025 |

---

## Side-by-Side Column Comparison

Complete column mapping showing exact position and name changes across all 5 schemas.

**Legend:** ⭐ = New tracking/metadata field | 🌍 = Location/classification field | **Bold** = Major rename or new field

| # | Schema 1 (2000-2015) | Schema 2 (2016-2020) | Schema 3 (2021-2024) | Schema 4 (2025) | Schema 5 (2021-2024-V2) |
|---|----------------------|----------------------|----------------------|-----------------|-------------------------|
| 1 | `Organization Name` | `Organization Name` | `Procuring Entity` | `Procuring Entity (PE)` | `Procuring Entity (PE)` |
| 2 | `Reference ID` | `Reference ID` | `Bid Reference No.` | `Region` 🌍 | `Region` 🌍 |
| 3 | `Solicitation No.` | `Solicitation No.` | `Solicitation No.` | `Province` 🌍 | `Province` 🌍 |
| 4 | `Notice Title` | `Notice Title` | `Notice Title` | `City/Municipality` 🌍 | `City/Municipality` 🌍 |
| 5 | `Publish Date` | `Publish Date` | `Notice Type` | `Government Branch` 🌍 | `Government Branch` 🌍 |
| 6 | `Classification` | `Classification` | `Classification` | `PE Organization Type` 🌍 | `PE Organization Type` 🌍 |
| 7 | `Notice Type` | `Notice Type` | `Procurement Mode` | `PE Organization Type (Grouped)` 🌍 | `PE Organization Type (Grouped)` 🌍 |
| 8 | `Business Category` | `Business Category` | `Business Category` | `Bid Reference No.` | `Bid Reference No.` |
| 9 | `Funding Source` | `Funding Source` | `Funding Source` | `Notice Title` | `Notice Title` |
| 10 | `Funding Instrument` | `Funding Instrument` | `Funding Instrument` | `Classification` | `Classification` |
| 11 | `Procurement Mode` | `Procurement Mode` | `Trade Agreement` | `Procurement Mode` | `Procurement Mode` |
| 12 | `Trade Agreement` | `Trade Agreement` | `Approved Budget of the Contract` | `Business Category` | `Business Category` |
| 13 | `Approved Budget of the Contract` | `Approved Budget of the Contract` | `Published Date` | `Funding Source` | `Funding Source` |
| 14 | `Area of Delivery` | `Area of Delivery` | `Closing Date` | `Funding Instrument` | `Funding Instrument` |
| 15 | `Contract Duration` | `Contract Duration` | `PreBid Date` | `Trade Agreement` | `Trade Agreement` |
| 16 | `Calendar Type` | `Calendar Type` | `Area of Delivery` | `Approved Budget of the Contract` | `Approved Budget of the Contract` |
| 17 | `Line Item No` | `Line Item No` | `Contract Duration` | `Published Date` | `Published Date` |
| 18 | `Item Name` | `Item Name` | `Calendar Type` | `Closing Date` | `Closing Date` |
| 19 | `Item Desc` | `Item Desc` | `Line Item No` | `Area of Delivery` | `Area of Delivery` |
| 20 | `Quantity` | `Quantity` | `Item Name` | `Contract Duration` | `Contract Duration` |
| 21 | **`UOM`** | **`Unit of Measurement`** | `Item Description` | `Calendar Type` | `Calendar Type` |
| 22 | `Item Budget` | `Item Budget` | `Quantity` | `Line Item No` | `Line Item No` |
| 23 | `PreBid Date` | `PreBid Date` | `UOM` | `Item Name` | `Item Name` |
| 24 | `Closing Date` | `Closing Date` | `Item Budget` | `Item Description` | `Item Description` |
| 25 | `Notice Status` | `Notice Status` | `Notice Status` | `Quantity` | `Quantity` |
| 26 | `Award No.` | `Award No.` | **`Created By`** ⭐ | `UOM` | `UOM` |
| 27 | `Award Title` | `Award Title` | `Award No.` | `Item Budget` | `Item Budget` |
| 28 | `Award Type` | `Award Type` | `Award Title` | **`Bid Notice Status`** | **`Bid Notice Status`** |
| 29 | `UNSPSC Code` | `UNSPSC Code` | `Award Type` | `Award Reference No.` | `Award Reference No.` |
| 30 | `UNSPSC Description` | `UNSPSC Description` | `UNSPSC Code` | `Award Title` | `Award Title` |
| 31 | `Awardee Corporate Title` | `Awardee Corporate Title` | `UNSPSC Description` | `UNSPSC Code` | `UNSPSC Code` |
| 32 | `Contract Amount` | `Contract Amount` | `Published Date(Award)` | `UNSPSC Description` | `UNSPSC Description` |
| 33 | `Contract No` | `Contract No` | `Award Date` | `Published Date(Award)` | `Published Date(Award)` |
| 34 | `Publish Date(Award)` | `Publish Date(Award)` | `Notice to Proceed Date` | `Award Date` | `Award Date` |
| 35 | `Award Date` | `Award Date` | `Contract No` | `Contract Amount` | `Contract Amount` |
| 36 | `Notice to Proceed Date` | `Notice to Proceed Date` | `Contract Amount` | **`Award Notice Status`** | **`Award Notice Status`** |
| 37 | `Contract Efectivity Date` ⚠️ | `Contract Efectivity Date` ⚠️ | `Contract Efectivity Date` ⚠️ | `Notice to Proceed Date` | `Notice to Proceed Date` |
| 38 | `Contract End Date` | `Contract End Date` | `Contract End Date` | `Contract Effectivity Date` ✅ | `Contract Effectivity Date` ✅ |
| 39 | `Reason for Award` | `Reason for Award` | `Award Status` | `Contract End Date` | `Contract End Date` |
| 40 | `Award Status` | `Award Status` | `Reason for Award` | `Awardee Organization Name` | `Awardee Organization Name` |
| 41 | — | — | `Awardee Organization Name` | **`Country of Awardee`** 🌍 | **`Country of Awardee`** 🌍 |
| 42 | — | — | **`Awardee Contact Person`** ⭐ | **`Region of Awardee`** 🌍 | **`Region of Awardee`** 🌍 |
| 43 | — | — | **`List of Bidder's`** ⭐ | **`Province of Awardee`** 🌍 | **`Province of Awardee`** 🌍 |
| 44 | — | — | — | **`City/Municipality of Awardee`** 🌍 | **`City/Municipality of Awardee`** 🌍 |
| 45 | — | — | — | **`Awardee Size`** 🌍 | **`Awardee Size`** 🌍 |
| 46 | — | — | — | **`Awardee Joint Venture`** 🌍 | **`Awardee Joint Venture`** 🌍 |

---

## Key Observations

1. **Location Fields** — Both PE and Awardee expanded from 1 field to 7 fields
2. **Core Procurement Fields** — Budget, funding, and procurement mode remain stable
3. **Privacy Removals** — User tracking and bidder list fields removed in 2025
4. **Legacy Field Removal** — Deprecated fields systematically eliminated
5. **Naming Standardization** — Status field names made consistent
