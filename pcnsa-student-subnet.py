import boto3
import sys

instance_id = sys.argv[1]

with open("../keys/aws_cli.txt","r") as f:
    keys_str = f.read()

keys = keys_str.split("\n")

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
)

ec2_client = session.client('ec2')

ec2_client.start_instances(
    InstanceIds=[
        instance_id,
    ],
    DryRun=True
)

print(keys)