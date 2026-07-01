# NCM Spare Parts Data Warehouse — Schema Design

## Overview
A star schema design for tracking spare parts spending across multiple
company sites, vehicles, and suppliers. Built to support data-driven
maintenance and purchasing decisions.

## Star Schema

dim_vehicle ──┐
dim_site ─────┤
dim_supplier ─┼──→ fact_spare_parts
dim_date ─────┘


## Design Decisions

### Why a star schema instead of one big table?
A star schema was used because of data integrity and query speed. This schema stores each entity once and is referenced by ID. Modifications can be done once and is applied through out the table

### Why surrogate keys (id) instead of using business keys (like CODE_PARC) directly as the primary key?
Surrogate keys are integers, and integer comparisons are faster than text comparisons when joining large tables.

### How are unmapped or unknown values handled (e.g. "STOCK", "Cash Purchase")?
Ignoring unmapped or unknown values will mean ignoring data such as amounts which is very important for the business. Unmapped values are inserted manually as unassigned rows

## Tables

**dim_vehicle** — equipment master data
**dim_site** — operating site locations
**dim_supplier** — vendors
**dim_date** — pre-computed date breakdowns for fast reporting
**fact_spare_parts** — individual spare parts transactions

## Tech Stack
- PostgreSQL (database)
- Python + pandas