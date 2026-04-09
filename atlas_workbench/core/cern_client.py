"""cernopendata-client wrapper for CERN Open Data record file URL discovery.

Fallback interface for retrieving file URLs by CERN Open Data record ID.
Handles the documented 'file indices vs files' pitfall: some records expose
files via indirect file-index JSON files rather than inline file lists.
"""

from __future__ import annotations

import json


class CernClientError(RuntimeError):
    """Raised when cernopendata-client fails or returns unusable results."""


def _expand_file_index(raw_locations: list[str]) -> list[str]:
    """Expand file-index JSON entries into individual data file URLs.

    CERN Open Data records sometimes expose a list of 'file_index' JSON
    files rather than individual data file URLs directly.  This helper
    fetches each .json file-index entry and extracts the contained URLs.

    Any URL that does not end in '_file_index.json' is returned unchanged.
    """
    import urllib.request

    expanded: list[str] = []
    for loc in raw_locations:
        if loc.endswith("_file_index.json"):
            try:
                with urllib.request.urlopen(loc, timeout=30) as resp:  # noqa: S310  # nosec B310
                    index_data = json.loads(resp.read())
                if isinstance(index_data, list):
                    for entry in index_data:
                        if isinstance(entry, dict):
                            uri = entry.get("uri") or entry.get("url") or entry.get("filename")
                            if uri:
                                expanded.append(str(uri))
                        elif isinstance(entry, str):
                            expanded.append(entry)
            except Exception:
                # If the index file is unreachable, fall back to the index URL itself
                expanded.append(loc)
        else:
            expanded.append(loc)
    return expanded


def get_file_locations(
    record_id: int,
    protocol: str = "root",
) -> list[str]:
    """Return file URLs for a CERN Open Data record.

    Uses cernopendata-client's searcher module to retrieve file locations.
    The result is passed through ``_expand_file_index`` to handle indirect
    file-index records.  URLs are filtered by ``protocol``: 'root' returns
    root:// URIs via xrootd, 'https' returns https:// URIs.

    Raises
    ------
    CernClientError
        If cernopendata_client raises or no URLs match the requested protocol.
    """
    try:
        from cernopendata_client import searcher  # type: ignore[import]
    except ImportError as exc:
        raise CernClientError(
            "cernopendata-client is not installed; run: pip install cernopendata-client==1.0.2"
        ) from exc

    # cernopendata_client uses 'xrootd' for root:// and 'http' for https://
    codc_protocol = "xrootd" if protocol == "root" else "http"
    server = searcher.SERVER_HTTP_URI

    try:
        record_json = searcher.get_record_as_json(server=server, recid=record_id)
        files_list = searcher.get_files_list(
            server=server,
            record_json=record_json,
            protocol=codc_protocol,
            expand=True,
        )
    except Exception as exc:
        raise CernClientError(
            f"cernopendata_client searcher failed for recid={record_id}, "
            f"protocol={protocol!r}: {exc}"
        ) from exc

    # get_files_list returns [(url, size, checksum), ...]
    raw: list[str] = [str(entry[0]) for entry in files_list if entry and entry[0]]

    urls = _expand_file_index([u for u in raw if u])

    if not urls:
        raise CernClientError(
            f"cernopendata-client returned no URLs for record {record_id} (protocol={protocol!r})"
        )

    return urls
