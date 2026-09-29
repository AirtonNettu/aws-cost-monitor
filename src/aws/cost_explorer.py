from datetime import date, timedelta

import boto3


def get_costs():
    client = boto3.client("ce", region_name="us-east-1")

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    response = client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.isoformat(),
            "End": end_date.isoformat(),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {
                "Type": "DIMENSION",
                "Key": "SERVICE",
            }
        ],
    )

    results = []

    for period in response["ResultsByTime"]:
        results.append(
            {
                "start": period["TimePeriod"]["Start"],
                "end": period["TimePeriod"]["End"],
                "estimated": period["Estimated"],
                "groups": period["Groups"],
            }
        )

    return results


if __name__ == "__main__":
    costs = get_costs()

    for cost in costs:
        print(cost)