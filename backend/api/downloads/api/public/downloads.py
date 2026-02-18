"""
Downloads Proxy API

GET /api/downloads/info        - Available downloads (dynamic from GitHub)
GET /api/downloads/{platform}  - Stream release asset for platform

Dynamically queries GitHub Releases API (cached 5 min) to resolve the
latest Aurity Desktop release per platform.  No hardcoded versions.
"""

import time

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.config.secrets import get_secret
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/downloads", tags=["downloads"])

GITHUB_REPO = "BernardUriza/free-intelligence"

# Filename suffix → platform mapping (Aurity Desktop naming convention)
PLATFORM_SUFFIX = {
    "windows": "_x64-setup.exe",
    "macos": "_aarch64.dmg",
    "linux": "_amd64.AppImage",
}

# ---------------------------------------------------------------------------
# GitHub releases cache (in-memory, 5 min TTL)
# ---------------------------------------------------------------------------
_cache: dict = {"releases": None, "ts": 0.0}
_CACHE_TTL = 300  # seconds


def _github_token() -> str:
    token = get_secret("GITHUB_TOKEN", default=None) or get_secret("GH_PAT", default=None)
    if not token:
        logger.error("No GitHub token configured for release downloads")
        raise HTTPException(status_code=503, detail="Download service not configured")
    return token


async def _fetch_releases(token: str) -> list[dict]:
    """Return recent non-draft releases, cached for 5 min."""
    now = time.time()
    if _cache["releases"] is not None and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["releases"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=10",
            headers=headers,
        )

    if resp.status_code != 200:
        logger.error("GitHub releases API returned %s", resp.status_code)
        if _cache["releases"] is not None:
            return _cache["releases"]  # stale > nothing
        raise HTTPException(status_code=502, detail="Failed to fetch releases from GitHub")

    releases = [r for r in resp.json() if not r.get("draft")]
    _cache["releases"] = releases
    _cache["ts"] = now
    return releases


def _find_asset(releases: list[dict], platform: str) -> tuple[dict, dict]:
    """Find the newest release that contains an Aurity Desktop asset for *platform*.

    Returns ``(release, asset)`` or raises 404.
    """
    suffix = PLATFORM_SUFFIX.get(platform)
    if suffix is None:
        raise HTTPException(
            status_code=404,
            detail=f"Platform '{platform}' not supported. Options: {list(PLATFORM_SUFFIX)}",
        )

    for release in releases:
        for asset in release.get("assets", []):
            name: str = asset.get("name", "")
            if name.startswith("Aurity") and name.endswith(suffix):
                return release, asset

    raise HTTPException(status_code=404, detail=f"No Aurity Desktop release found for {platform}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/info")
async def get_download_info() -> dict:
    """Return available downloads — resolved dynamically from GitHub.

    Shape matches what the frontend ``ReleasesData`` interface expects so the
    downloads page can consume it without changes.
    """
    token = _github_token()
    releases = await _fetch_releases(token)

    platforms: dict = {}
    latest_version = "unknown"
    latest_date = ""

    for platform in PLATFORM_SUFFIX:
        try:
            release, asset = _find_asset(releases, platform)
            version = release["tag_name"].lstrip("v")
            if latest_version == "unknown":
                latest_version = version
                latest_date = release.get("published_at", "")[:10]
            platforms[platform] = {
                "url": f"/api/downloads/{platform}",
                "size": f"{asset['size'] / (1024 * 1024):.0f} MB",
                "sha256": "",
            }
        except HTTPException:
            pass  # platform simply not available yet

    return {
        "releases": [
            {
                "version": latest_version,
                "date": latest_date,
                "platforms": platforms,
                "changelog": [],
            }
        ],
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "github-api",
    }


@router.get("/{platform}")
async def download_release(platform: str):
    """Stream the release binary for *platform* from GitHub."""
    platform = platform.lower()

    token = _github_token()
    releases = await _fetch_releases(token)
    _, asset = _find_asset(releases, platform)

    asset_url = asset["url"]
    filename = asset["name"]

    download_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/octet-stream",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async def stream_file():
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream(
                "GET", asset_url, headers=download_headers, timeout=300.0
            ) as resp:
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail="Failed to download asset from GitHub",
                    )
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(
        stream_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )
