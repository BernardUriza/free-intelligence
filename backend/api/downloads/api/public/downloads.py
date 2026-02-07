"""
Downloads Proxy API

GET /api/downloads/{platform}

Proxies GitHub release assets for private repository downloads.
Since the repo is private, users can't download directly from GitHub.
This endpoint fetches the asset using authenticated GitHub API and
streams it to the user.

Supported platforms: windows, macos, linux
"""

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config.secrets import get_secret
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/downloads", tags=["downloads"])

# Release assets configuration
# Update these when new versions are released
RELEASE_ASSETS = {
    "windows": {
        "tag": "v1.0.14",
        "filename": "Aurity_1.0.14_x64-setup.exe",
        "content_type": "application/octet-stream",
    },
    "macos": {
        "tag": "v1.0.12",
        "filename": "Aurity_1.0.12_aarch64.dmg",
        "content_type": "application/octet-stream",
    },
    # Linux disabled for now
    # "linux": {
    #     "tag": "v1.0.x",
    #     "filename": "Aurity_1.0.x_amd64.AppImage",
    #     "content_type": "application/octet-stream",
    # },
}

GITHUB_REPO = "BernardUriza/free-intelligence"


class DownloadInfo(BaseModel):
    """Download information response."""
    platform: str
    version: str
    filename: str
    download_url: str


@router.get("/info")
async def get_download_info() -> dict:
    """Get available downloads information."""
    downloads = {}
    for platform, asset in RELEASE_ASSETS.items():
        downloads[platform] = {
            "version": asset["tag"].lstrip("v"),
            "filename": asset["filename"],
            "download_url": f"/api/downloads/{platform}",
        }
    return {"downloads": downloads}


@router.get("/{platform}")
async def download_release(platform: str):
    """
    Download release asset for the specified platform.

    Streams the file from GitHub releases using authenticated API access.
    """
    platform = platform.lower()

    if platform not in RELEASE_ASSETS:
        raise HTTPException(
            status_code=404,
            detail=f"Platform '{platform}' not available. Supported: {list(RELEASE_ASSETS.keys())}"
        )

    asset = RELEASE_ASSETS[platform]
    tag = asset["tag"]
    filename = asset["filename"]

    # Get GitHub token from secrets
    github_token = get_secret("GITHUB_TOKEN", default=None)
    if not github_token:
        # Try alternative secret names
        github_token = get_secret("GH_PAT", default=None)

    if not github_token:
        logger.error("No GitHub token configured for release downloads")
        raise HTTPException(
            status_code=503,
            detail="Download service not configured"
        )

    # First, get the asset ID from GitHub API
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        # Get release info
        response = await client.get(api_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get release info: {response.status_code}")
            raise HTTPException(status_code=404, detail="Release not found")

        release_data = response.json()

        # Find the asset
        asset_info = None
        for a in release_data.get("assets", []):
            if a["name"] == filename:
                asset_info = a
                break

        if not asset_info:
            logger.error(f"Asset {filename} not found in release {tag}")
            raise HTTPException(status_code=404, detail="Asset not found")

        # Get the asset download URL (requires special Accept header)
        asset_url = asset_info["url"]
        download_headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Stream the file
        async def stream_file():
            async with httpx.AsyncClient(follow_redirects=True) as stream_client:
                async with stream_client.stream(
                    "GET",
                    asset_url,
                    headers=download_headers,
                    timeout=300.0,  # 5 min timeout for large files
                ) as stream_response:
                    if stream_response.status_code != 200:
                        raise HTTPException(
                            status_code=stream_response.status_code,
                            detail="Failed to download asset"
                        )
                    async for chunk in stream_response.aiter_bytes(chunk_size=65536):
                        yield chunk

        return StreamingResponse(
            stream_file(),
            media_type=asset["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "public, max-age=86400",  # Cache for 1 day
            }
        )
