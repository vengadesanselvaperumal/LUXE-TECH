from ipaddress import ip_address
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PLATFORM_HOSTS = {
    "instagram": ("instagram.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "tiktok": ("tiktok.com",),
    "pinterest": ("pinterest.com",),
}
SUPPORTED_PLATFORMS = frozenset((*PLATFORM_HOSTS, "other"))
TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "igshid", "si"})


def normalize_social_source_url(platform: str, source_url: str) -> str:
    """Validate and normalize a submitted public post URL without requesting it."""
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError("Select a supported social platform.")
    if len(source_url) > 2048:
        raise ValueError("Source URL must be 2048 characters or fewer.")

    try:
        parsed = urlsplit(source_url.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise ValueError("Enter a valid public post URL.") from None
    try:
        address = ip_address(hostname)
    except ValueError:
        address = None

    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or port not in (None, 443)
        or address is not None
        or "." not in hostname
    ):
        raise ValueError("Enter a public HTTPS post URL.")

    if platform in PLATFORM_HOSTS and not any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in PLATFORM_HOSTS[platform]
    ):
        raise ValueError("The source URL does not match the selected platform.")

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    path_parts = [part for part in parsed.path.split("/") if part]
    query = [
        (key, value)
        for key, value in query_pairs
        if not key.lower().startswith("utm_")
        and key.lower() not in TRACKING_PARAMETERS
    ]
    if platform == "instagram":
        if len(path_parts) < 2 or path_parts[0].lower() not in {"p", "reel", "reels", "tv"}:
            raise ValueError("Enter a public Instagram post, Reel, or video URL.")
        path = f"/{path_parts[0].lower()}/{path_parts[1]}"
        query = []
        hostname = "www.instagram.com"
    elif platform == "youtube":
        video_id = next((value for key, value in query_pairs if key == "v"), None)
        if hostname == "youtu.be" and path_parts:
            video_id = path_parts[0]
        elif len(path_parts) >= 2 and path_parts[0].lower() in {"shorts", "embed", "live"}:
            video_id = path_parts[1]
        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
            raise ValueError("Enter a valid public YouTube video URL.")
        hostname = "www.youtube.com"
        path = "/watch"
        query = [("v", video_id)]
    elif platform == "tiktok":
        if len(path_parts) < 3 or not re.fullmatch(r"@[^/]{1,64}", path_parts[0]) or path_parts[1].lower() != "video" or not path_parts[2].isdigit():
            raise ValueError("Enter a public TikTok video URL.")
        path = f"/{path_parts[0]}/video/{path_parts[2]}"
        query = []
        hostname = "www.tiktok.com"
    elif platform == "pinterest":
        if len(path_parts) < 2 or path_parts[0].lower() != "pin" or not path_parts[1].isdigit():
            raise ValueError("Enter a public Pinterest Pin URL.")
        path = f"/pin/{path_parts[1]}"
        query = []
        hostname = "www.pinterest.com"
    else:
        path = parsed.path.rstrip("/") or "/"
        query = [
            (key, value)
            for key, value in query
            if key.lower() not in TRACKING_PARAMETERS
        ]
    return urlunsplit(("https", hostname, path, urlencode(query), ""))
