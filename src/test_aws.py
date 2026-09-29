import boto3

sts = boto3.client("sts")

response = sts.get_caller_identity()

print("AWS conectada com sucesso")
print(f"Account: {response['Account']}")
print(f"ARN: {response['Arn']}")