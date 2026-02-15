from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path


def guess_mime_type(filename: str) -> str:
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"


def make_storage_path(
    *,
    group_id: str,
    bottle_id: str,
    member_id: str,
    media_type: str,
    filename: str,
) -> str:
    safe_name = Path(filename).name.replace(" ", "_")
    uid = uuid.uuid4().hex
    return f"groups/{group_id}/bottles/{bottle_id}/members/{member_id}/{media_type}/{uid}_{safe_name}"


def public_object_url(supabase_url: str, bucket: str, path: str) -> str:
    return f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
