"""Ensure the S3/RustFS bucket exists and is **public-read** — product images are public assets the
browser loads directly from the bucket (arvel ``disk.url()``), so the bucket must allow anonymous
``s3:GetObject``. Idempotent; run via ``make bucket`` (also part of ``make setup``). Uses botocore
(a transitive dep via s3fs) so it needs no extra tooling."""

import json
import sys

sys.path.insert(0, ".")

from botocore.exceptions import ClientError  # noqa: E402
from botocore.session import Session  # noqa: E402

from arvel import config  # noqa: E402
from bootstrap.app import create_app  # noqa: E402
from arvel.kernel import set_application  # noqa: E402
from arvel.kernel.bootstrap import bootstrap_app  # noqa: E402


def main() -> None:
    app = create_app()
    set_application(app)
    bootstrap_app(app)

    s3 = config("filesystems.disks.s3") or {}
    bucket = s3.get("bucket")
    if not bucket:
        print("no s3 bucket configured (FILESYSTEM_DISK is not s3) — nothing to do")
        return

    client = Session().create_client(
        "s3",
        endpoint_url=s3.get("endpoint_url"),
        aws_access_key_id=s3.get("key"),
        aws_secret_access_key=s3.get("secret"),
        region_name=s3.get("region") or "us-east-1",
    )

    try:
        client.create_bucket(Bucket=bucket)
        print(f"created bucket '{bucket}'")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"bucket '{bucket}' already exists")
        else:
            raise

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    print(f"bucket '{bucket}' is public-read (anonymous s3:GetObject)")


if __name__ == "__main__":
    main()
