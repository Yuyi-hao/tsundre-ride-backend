from urllib.parse import urlparse

from .client import StorageClient


storage_client = StorageClient()


def upload_a_file(file, bucket, path, content_type=None):
    return storage_client.upload_file(
        file=file,
        bucket=bucket,
        key=path,
        content_type=content_type,
    )


def delete_file(file_url):
    bucket, key = _parse_storage_url(file_url)
    storage_client.delete_file(
        bucket=bucket,
        key=key,
    )


def get_file(file_url):
    bucket, key = _parse_storage_url(file_url)
    return storage_client.get_file(
        bucket=bucket,
        key=key,
    )


def get_presigned_url(file_url, expires_in=3600):
    bucket, key = _parse_storage_url(file_url)

    return storage_client.generate_presigned_url(
        bucket=bucket,
        key=key,
        expires_in=expires_in,
    )


def get_summary():
    buckets = storage_client.list_buckets()

    return [
        storage_client.get_bucket_summary(bucket)
        for bucket in buckets
    ]


def _parse_storage_url(file_url):
    """
    Convert a storage URL into bucket + object key.

    Example:

        http://localhost:9000/challenge-files/foo/bar.html

    becomes:

        bucket = challenge-files
        key = foo/bar.html
    """

    parsed = urlparse(file_url)

    path = parsed.path.lstrip("/")

    if not path:
        raise ValueError("Invalid storage URL")

    parts = path.split("/", 1)

    if len(parts) != 2:
        raise ValueError("Invalid storage URL")

    bucket, key = parts

    return bucket, key