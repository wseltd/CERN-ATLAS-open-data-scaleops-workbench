"""atlasopenmagic client wrapper for ATLAS Open Data URL discovery.

Primary interface for retrieving DAOD_PHYSLITE file URLs by DSID.
Falls back to 'https' protocol when 'root' returns an empty list.
"""

from __future__ import annotations


class AtlasClientError(RuntimeError):
    """Raised when atlasopenmagic fails or returns unusable results."""

    def __repr__(self) -> str:
        return f"AtlasClientError({self.args[0]!r})" if self.args else "AtlasClientError()"


def _strip_simplecache(url: str) -> str:
    """Remove fsspec simplecache:: prefix if present.

    atlasopenmagic can return URLs like 'simplecache::root://...' when
    caching is enabled.  The canonical URL for hashing and storage must
    never carry the simplecache prefix.
    """
    prefix = "simplecache::"
    if url.startswith(prefix):
        return url[len(prefix) :]
    return url


def get_urls(
    dsid: int,
    release_tag: str,
    protocol: str = "root",
) -> list[str]:
    """Return a list of canonical file URLs for a given DSID and release tag.

    Tries ``protocol`` first; if the result is empty and protocol is 'root',
    retries with 'https' as a fallback.  All returned URLs have the
    'simplecache::' prefix stripped.

    Raises
    ------
    AtlasClientError
        If atlasopenmagic raises an exception or both protocols return empty.
    """
    try:
        import atlasopenmagic as atom  # type: ignore[import]
    except ImportError as exc:
        raise AtlasClientError(
            "atlasopenmagic is not installed; run: pip install atlasopenmagic==1.9.0"
        ) from exc

    try:
        urls: list[str] = atom.get_urls(dsid, release_tag, protocol=protocol)
    except Exception as exc:
        raise AtlasClientError(
            f"atlasopenmagic.get_urls({dsid!r}, {release_tag!r}, protocol={protocol!r}) "
            f"failed: {exc}"
        ) from exc

    urls = [_strip_simplecache(u) for u in urls if u]

    if not urls and protocol == "root":
        # Transparent fallback: retry with https
        try:
            urls = atom.get_urls(dsid, release_tag, protocol="https")
        except Exception as exc:
            raise AtlasClientError(
                f"atlasopenmagic https fallback also failed for DSID {dsid}: {exc}"
            ) from exc
        urls = [_strip_simplecache(u) for u in urls if u]

    if not urls:
        raise AtlasClientError(
            f"atlasopenmagic returned no URLs for DSID {dsid} "
            f"(release_tag={release_tag!r}, protocol={protocol!r})"
        )

    return urls
