"""Create the configured S3 bucket on MinIO (or AWS) if it does not exist.

Run from repo root with apps/api on PYTHONPATH and deps installed, e.g.:

    cd apps/api
    python scripts/ensure_minio_bucket.py
"""

from __future__ import annotations

import os
import sys

import boto3
from botocore.exceptions import ClientError


def main() -> int:
    endpoint = (os.environ.get("S3_ENDPOINT_URL") or "").strip()
    bucket = (os.environ.get("S3_BUCKET_DOCUMENTS") or "documents").strip()
    access = (os.environ.get("S3_ACCESS_KEY_ID") or "").strip()
    secret = (os.environ.get("S3_SECRET_ACCESS_KEY") or "").strip()
    region = (os.environ.get("S3_REGION") or "us-east-1").strip()

    if not endpoint:
        print("S3_ENDPOINT_URL not set; skipping bucket ensure (not using S3-compatible storage).")
        return 0

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access or None,
        aws_secret_access_key=secret or None,
        region_name=region,
    )
    try:
        client.head_bucket(Bucket=bucket)
        print(f"Bucket exists: {bucket}")
        return 0
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("404", "403", "NoSuchBucket"):
            print(f"head_bucket failed: {code} {exc}", file=sys.stderr)
            return 1
    try:
        client.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "BucketAlreadyOwnedByYou":
            print(f"Bucket already owned: {bucket}")
            return 0
        print(f"create_bucket failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
