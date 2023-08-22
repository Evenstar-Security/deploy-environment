import boto3

with open("../keys/aws_cli.txt","r") as f:
    keys_str = f.read()

keys = keys_str.split("\n")

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
)

print(keys)