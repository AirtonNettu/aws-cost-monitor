"""Invariantes estáticas: nenhuma chamada AWS é necessária."""

from pathlib import Path
from cfnlint.decode import decode


def test_template_preserva_privacidade_e_limites():
    template, errors = decode(
        str(Path(__file__).resolve().parents[1] / "infra/serverless.yaml")
    )
    assert not errors
    resources = template["Resources"]
    bucket = resources["ReportsBucket"]
    assert all(bucket["Properties"]["PublicAccessBlockConfiguration"].values())
    assert bucket["DeletionPolicy"] == bucket["UpdateReplacePolicy"] == "Retain"
    assert resources["CollectorLogGroup"]["DeletionPolicy"] == "Retain"
    assert resources["Collector"]["Properties"]["Timeout"] == 60
    assert resources["Collector"]["Properties"]["ReservedConcurrentExecutions"] == 1
    assert template["Parameters"]["ScheduleState"]["Default"] == "DISABLED"
    assert resources["AsyncInvocation"]["Properties"]["MaximumRetryAttempts"] == 0
    assert (
        resources["DailySchedule"]["Properties"]["Targets"][0]["RetryPolicy"][
            "MaximumRetryAttempts"
        ]
        == 0
    )
    statements = resources["CollectorRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]["Statement"]
    listing = next(s for s in statements if s.get("Action") == "s3:ListBucket")
    assert listing["Resource"] == {"Fn::GetAtt": ["ReportsBucket", "Arn"]}
    assert listing["Condition"]["StringLike"]["s3:prefix"] == "reports/*"
    assert listing["Condition"]["NumericLessThanEquals"]["s3:max-keys"] == "1"
    assert not any("DeleteObject" in str(s.get("Action")) for s in statements)
    rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]
    report = next(r for r in rules if r["Id"] == "RetencaoDeRelatorios")
    assert report["Prefix"] == "reports/"
    assert report["ExpirationInDays"] == {"Ref": "ReportRetentionDays"}
