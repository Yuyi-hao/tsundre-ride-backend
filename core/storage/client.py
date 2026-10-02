import os

import boto3
from botocore.config import Config
from core import settings

class StorageClient:
    def __init__(self):
        endpoint = settings.STORAGE_ENDPOINT

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION,
            use_ssl=settings.STORAGE_USE_SSL == "true",
            config=Config(signature_version="s3v4"),
        )

    def upload_file(self, file, bucket, key, content_type=None):
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        
        self.client.upload_fileobj(file, bucket, key, ExtraArgs=extra_args)

        return f"{self.client.meta.endpoint_url}/{bucket}/{key}"

    
    def delete_file(self, bucket, key):
        self.client.delete_object(Bucket=bucket, Key=key)

    def get_file(self, bucket, key):
        return self.client.get_object(Bucket=bucket, Key=key)

    def generate_presigned_url(self, bucket, key, expires_in=3600):
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )

    def get_bucket_summary(self, bucket):
        total_size = 0
        object_count = 0

        paginator = self.client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                object_count += 1
                total_size += obj["Size"]

        return {
            "bucket": bucket,
            "object_count": object_count,
            "total_size": total_size,
        }

    def list_buckets(self):
        response = self.client.list_buckets()

        return [
            bucket["Name"]
            for bucket in response.get("Buckets", [])
        ]

