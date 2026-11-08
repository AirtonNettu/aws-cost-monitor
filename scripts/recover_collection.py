"""Inspeciona reservas e prepara recuperação explícita; não libera guardas por exclusão."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.operations.collection import inspect_job, recover_once


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=["local-status", "local-recover", "s3-status", "s3-event"]
    )
    parser.add_argument("--database", default="data/costs.db")
    parser.add_argument("--bucket")
    parser.add_argument("--expected-token")
    parser.add_argument("--expected-etag")
    parser.add_argument("--confirm-stopped", action="store_true")
    parser.add_argument("--allow-paid-retry", action="store_true")
    parser.add_argument("--allow-aws-read", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "local-status":
            result = inspect_job(args.database)
        elif args.operation == "local-recover":
            if (
                not args.confirm_stopped
                or not args.allow_paid_retry
                or not args.expected_token
            ):
                parser.error("Confirme parada, possível cobrança e token observado.")
            result = {
                "run_id": recover_once(
                    args.database,
                    expected_token=args.expected_token,
                    confirm_stopped=True,
                )
            }
        elif args.operation == "s3-status":
            if not args.allow_aws_read or not args.bucket:
                parser.error("Leitura AWS exige bucket e --allow-aws-read explícitos.")
            import boto3
            from src.operations.serverless import inspect_guard, SDK_CONFIG

            guard, etag = inspect_guard(
                boto3.client("s3", config=SDK_CONFIG),
                args.bucket,
                datetime.now(timezone.utc).date().isoformat(),
            )
            result = {**guard, "etag": etag}
        else:
            if (
                not args.confirm_stopped
                or not args.allow_paid_retry
                or not args.expected_token
                or not args.expected_etag
            ):
                parser.error(
                    "Confirme parada, possível cobrança, token e ETag observados."
                )
            # Somente gera JSON: este comando não invoca função nem consulta AWS.
            result = {
                "recovery": {
                    "confirm_stopped": True,
                    "allow_paid_retry": True,
                    "expected_token": args.expected_token,
                    "expected_etag": args.expected_etag,
                }
            }
        print(json.dumps(result))
        return 0
    except Exception:
        print(
            json.dumps(
                {
                    "error": "RECOVERY_BLOCKED",
                    "message": "Verifique reserva, esquema, exclusão de escritores e runbook.",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
