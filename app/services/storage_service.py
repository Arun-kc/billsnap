"""
S3-compatible storage service (works with Supabase Storage, Cloudflare R2, or AWS S3).
All objects are private; access is via short-lived signed URLs.
"""

import io
import uuid
from datetime import date

import boto3
from botocore.config import Config
from PIL import Image

from ..config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url or None,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )


def _upload_key(user_id: uuid.UUID, job_id: uuid.UUID, ext: str, bill_date: date | None = None) -> str:
    d = bill_date or date.today()
    return f"uploads/{user_id}/{d.year}/{d.month:02d}/{job_id}.{ext}"


def _thumbnail_key(user_id: uuid.UUID, job_id: uuid.UUID, bill_date: date | None = None) -> str:
    d = bill_date or date.today()
    return f"thumbnails/{user_id}/{d.year}/{d.month:02d}/{job_id}_thumb.webp"


def upload_bill(
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    file_bytes: bytes,
    content_type: str,
    ext: str,
) -> str:
    """Upload original bill file to S3. Returns the S3 key."""
    key = _upload_key(user_id, job_id, ext)
    _client().put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key


def upload_thumbnail(
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    image_bytes: bytes,
) -> str:
    """Generate a WebP thumbnail and upload it. Returns the S3 key."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=75)
    buf.seek(0)

    key = _thumbnail_key(user_id, job_id)
    _client().put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=buf.read(),
        ContentType="image/webp",
    )
    return key


def download(key: str) -> bytes:
    """Download a file from S3 and return its bytes."""
    response = _client().get_object(Bucket=settings.storage_bucket, Key=key)
    return response["Body"].read()


def signed_url(key: str | None) -> str | None:
    """Generate a short-lived signed URL for private object access."""
    if not key:
        return None
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=settings.signed_url_ttl,
    )


def delete(key: str) -> None:
    """Delete an object from S3."""
    _client().delete_object(Bucket=settings.storage_bucket, Key=key)
