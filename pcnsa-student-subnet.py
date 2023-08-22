import boto3
import sys

#instance_id = sys.argv[1]

with open("../keys/aws_cli.txt","r") as f:
    keys_str = f.read()

keys = keys_str.split("\n")

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
    region_name="us-east-1"
)

ec2_client = session.client('ec2')

ec2_client.run_instances(
    LaunchTemplate={
        'LaunchTemplateName': 'PCNSA-Student-FW',
        'Version': '3'
    },
    MinCount = 1,
    MaxCount = 1
)