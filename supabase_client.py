"""
Supabase Client & Dual-Mode Data Provider
-----------------------------------------
Enables:
1. Live Supabase database querying (structured tables + pgvector RPC) when
   SUPABASE_URL and SUPABASE_KEY are set in .env.
2. Graceful fallback to local JSON & InMemoryVectorStore when credentials are not configured,
   ensuring zero-setup local execution.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SECRET_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

_SUPABASE_CLIENT = None


def get_supabase_client():
    """Initializes and caches the Supabase client if configured."""
    global _SUPABASE_CLIENT
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    if _SUPABASE_CLIENT is None:
        try:
            from supabase import create_client
            _SUPABASE_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"[Supabase Warning] Could not connect to Supabase: {e}. Using local storage.")
            return None

    return _SUPABASE_CLIENT


def is_supabase_enabled() -> bool:
    """Returns True if connected to live Supabase."""
    return get_supabase_client() is not None


def query_records(table: str, identifier: str = "") -> List[Dict[str, Any]]:
    """
    Queries records from either Supabase (if configured) or local data/ops_database.json.
    """
    client = get_supabase_client()
    table_clean = table.strip().lower()

    # 1. Live Supabase Query
    if client:
        try:
            query = client.table(table_clean).select("*")
            if identifier:
                # Search by id or match across text columns
                if table_clean == "clients":
                    query = query.or_(f"id.ilike.%{identifier}%,name.ilike.%{identifier}%")
                elif table_clean == "tasks":
                    query = query.or_(f"id.ilike.%{identifier}%,title.ilike.%{identifier}%,status.ilike.%{identifier}%,assigned_to.ilike.%{identifier}%")
            response = query.execute()
            return response.data or []
        except Exception as e:
            print(f"[Supabase Error]: {e}. Falling back to local data.")

    # 2. Local Fallback (data/ops_database.json)
    db_path = Path(__file__).parent / "data" / "ops_database.json"
    if not db_path.exists():
        return []

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if table_clean not in data:
        return []

    records = data[table_clean]
    if not identifier:
        return records

    identifier_clean = identifier.strip().lower()
    filtered = []
    for record in records:
        match_id = record.get("id", "").lower() == identifier_clean
        match_name = identifier_clean in record.get("name", "").lower()
        match_title = identifier_clean in record.get("title", "").lower()
        match_client = identifier_clean in record.get("client_id", "").lower()
        match_status = identifier_clean in record.get("status", "").lower()
        match_assignee = identifier_clean in record.get("assigned_to", "").lower()
        if match_id or match_name or match_title or match_client or match_status or match_assignee:
            filtered.append(record)

    return filtered
