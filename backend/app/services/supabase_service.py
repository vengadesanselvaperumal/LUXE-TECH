import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("luxe_tech.supabase")
PUBLIC_BUCKETS = frozenset({"trend-images", "collections"})
SIGNED_URL_EXPIRES_SECONDS = 3600

_backend_root = Path(__file__).resolve().parent.parent.parent
if (_backend_root.parent / "uploads").exists():
    LOCAL_STORAGE_DIR = _backend_root.parent / "uploads"
elif (_backend_root / "uploads").exists():
    LOCAL_STORAGE_DIR = _backend_root / "uploads"
else:
    LOCAL_STORAGE_DIR = Path("./uploads").resolve()
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class SupabaseService:
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        self.anon_key = settings.SUPABASE_ANON_KEY or ""
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.active_key = self.service_key or self.anon_key

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.active_key)

    def _headers(self, use_service_role: bool = True) -> Dict[str, str]:
        key = self.service_key if (use_service_role and self.service_key) else self.active_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def upload_file(self, bucket: str, path: str, content: bytes, content_type: str = "image/jpeg") -> str:
        """
        Upload file to Supabase Storage if configured; otherwise store locally and return local file path / URL.
        """
        clean_path = path.lstrip("/")

        if self.is_configured:
            url = f"{self.supabase_url}/storage/v1/object/{bucket}/{clean_path}"
            headers = {
                "apikey": self.active_key,
                "Authorization": f"Bearer {self.active_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, content=content, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Supabase Storage request failed (%s).",
                    type(exc).__name__,
                )
                raise RuntimeError(
                    "Supabase Storage upload failed; local fallback is disabled while Supabase is configured."
                ) from None
            else:
                if resp.status_code in (200, 201):
                    if bucket in PUBLIC_BUCKETS:
                        return self.get_public_url(bucket, clean_path)
                    return await self._create_signed_url(bucket, clean_path)
                logger.warning(
                    "Supabase Storage upload returned HTTP %s.",
                    resp.status_code,
                )
                raise RuntimeError(
                    "Supabase Storage upload failed; local fallback is disabled while Supabase is configured."
                )

        # Local storage is only used when no Supabase Storage provider is configured.
        bucket_dir = LOCAL_STORAGE_DIR / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        local_file = bucket_dir / clean_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        with open(local_file, "wb") as f:
            f.write(content)

        return f"/api/images/local/{bucket}/{clean_path}"

    async def delete_file(self, bucket: str, path: str) -> None:
        """Delete a specific object previously uploaded by this backend."""
        clean_path = path.lstrip("/")
        if self.is_configured:
            url = f"{self.supabase_url}/storage/v1/object/{bucket}/{clean_path}"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.delete(url, headers=self._headers(use_service_role=True))
            except httpx.HTTPError as exc:
                logger.warning("Supabase Storage delete failed (%s).", type(exc).__name__)
                raise RuntimeError("Uploaded image cleanup failed.") from None
            if response.status_code not in (200, 204):
                logger.warning("Supabase Storage delete returned HTTP %s.", response.status_code)
                raise RuntimeError("Uploaded image cleanup failed.")
            return

        bucket_root = (LOCAL_STORAGE_DIR / bucket).resolve()
        file_path = (bucket_root / clean_path).resolve()
        if not file_path.is_relative_to(bucket_root):
            raise ValueError("Invalid storage object path.")
        if file_path.exists():
            file_path.unlink()

    def get_public_url(self, bucket: str, path: str) -> str:
        if bucket not in PUBLIC_BUCKETS:
            raise ValueError(f"Bucket '{bucket}' is not configured for public access.")
        if self.is_configured:
            clean_path = path.lstrip("/")
            return f"{self.supabase_url}/storage/v1/object/public/{bucket}/{clean_path}"
        return f"/api/images/local/{bucket}/{path.lstrip('/')}"

    async def create_signed_url(self, bucket: str, path: str) -> str:
        return await self._create_signed_url(bucket, path)

    async def _create_signed_url(self, bucket: str, path: str) -> str:
        clean_path = path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/sign/{bucket}/{clean_path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={"expiresIn": SIGNED_URL_EXPIRES_SECONDS},
                    headers=self._headers(use_service_role=True),
                )
            if response.status_code not in (200, 201):
                logger.warning(
                    "Supabase Storage signed-URL request returned HTTP %s.",
                    response.status_code,
                )
                raise RuntimeError("Private image retrieval URL could not be created.")
            payload = response.json()
            signed_url = payload.get("signedURL") if isinstance(payload, dict) else None
            if not isinstance(signed_url, str) or not signed_url:
                raise RuntimeError("Supabase Storage returned an invalid signed-URL response.")
            if signed_url.startswith(("http://", "https://")):
                return signed_url
            if signed_url.startswith("/storage/v1/"):
                return f"{self.supabase_url}{signed_url}"
            return f"{self.supabase_url}/storage/v1/{signed_url.lstrip('/')}"
        except httpx.HTTPError as exc:
            logger.warning(
                "Supabase Storage signed-URL request failed (%s).",
                type(exc).__name__,
            )
            raise RuntimeError("Private image retrieval URL could not be created.") from None

    async def select(self, table: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query a Supabase table via PostgREST
        """
        if not self.is_configured:
            return []
        url = f"{self.supabase_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=query_params or {}, headers=self._headers(use_service_role=False))
            if resp.status_code != 200:
                logger.warning("Supabase PostgREST select returned HTTP %s.", resp.status_code)
                raise RuntimeError(f"Supabase PostgREST select failed with HTTP {resp.status_code}.")
            result = resp.json()
            if not isinstance(result, list) or not all(isinstance(row, dict) for row in result):
                raise RuntimeError("Supabase PostgREST select returned an unexpected response shape.")
            return result
        except Exception as exc:
            logger.warning("Supabase PostgREST select failed (%s).", type(exc).__name__)
            raise

    async def insert(self, table: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert record into Supabase table
        """
        if not self.is_configured:
            return None
        url = f"{self.supabase_url}/rest/v1/{table}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=self._headers(use_service_role=True))
            if resp.status_code not in (200, 201):
                logger.warning("Supabase PostgREST insert returned HTTP %s.", resp.status_code)
                raise RuntimeError(f"Supabase PostgREST insert failed with HTTP {resp.status_code}.")
            result = resp.json()
            if isinstance(result, list):
                if result and isinstance(result[0], dict):
                    return result[0]
                return None
            if isinstance(result, dict):
                return result
            raise RuntimeError("Supabase PostgREST insert returned an unexpected response shape.")
        except Exception as exc:
            logger.warning("Supabase PostgREST insert failed (%s).", type(exc).__name__)
            raise


supabase_service = SupabaseService()
