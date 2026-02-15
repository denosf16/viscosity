from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from supabase import create_client

EXCEL_PATH = Path(__file__).resolve().parents[1] / "data" / "bourbon_list.xlsx"
SHEET_NAME = "250+ Bourbon Labels"
CHUNK_SIZE = 200


def _clean_str(x) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def main() -> None:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found at: {EXCEL_PATH}")

    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not service_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_KEY env var. Set it in PowerShell before running.")

    url = st.secrets["SUPABASE_URL"]
    sb = create_client(url, service_key)

    # Safety: prevent double seeding unless explicitly forced
    existing = sb.table("bottles").select("id").limit(1).execute().data
    if existing:
        raise RuntimeError(
            "bottles table already has rows. To avoid duplicates, aborting seed. "
            "If you truly want to reseed, truncate the table in Supabase first."
        )

    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    df.columns = [str(c).strip() for c in df.columns]

    records = []
    for _, r in df.iterrows():
        brand = _clean_str(r.get("Brand / Label"))
        expression = _clean_str(r.get("Expression / Line"))
        distillery = _clean_str(r.get("Distillery (Production)"))
        distillery_location = _clean_str(r.get("Distillery Location"))
        parent_company = _clean_str(r.get("Parent Company / Owner"))
        mashbill_style = _clean_str(r.get("Mashbill Style"))
        category = _clean_str(r.get("Category (Core / Limited / Allocated / Craft / Sourced)"))

        if not brand:
            continue

        records.append(
            {
                "brand": brand,
                "expression": expression,
                "distillery": distillery,
                "distillery_location": distillery_location,
                "parent_company": parent_company,
                "mashbill_style": mashbill_style,
                "category": category,
            }
        )

    # Dedupe to be safe (brand + expression + distillery)
    dedup = {}
    for rec in records:
        key = (
            (rec["brand"] or "").lower(),
            (rec["expression"] or "").lower(),
            (rec["distillery"] or "").lower(),
        )
        dedup[key] = rec

    records = list(dedup.values())

    inserted = 0
    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        sb.table("bottles").insert(chunk).execute()
        inserted += len(chunk)

    print(f"Seed complete. Inserted bottles: {inserted}")


if __name__ == "__main__":
    main()
