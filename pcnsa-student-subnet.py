import boto3

with open("../keys/aws_cli.txt","r") as f:
    keys = f.readlines()

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
)