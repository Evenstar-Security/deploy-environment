import boto3
import json

student_num = 1

with open("../keys/aws_cli.txt","r") as f:
    keys_str = f.read()

with open("../sysinfo/studentfw.txt","r") as f:
    sysinfo = json.load(f)


keys = keys_str.split("\n")

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
    region_name=sysinfo["region"]
)

ec2_client = session.client('ec2')


response = ec2_client.run_instances(
    LaunchTemplate={
        'LaunchTemplateName': sysinfo['template'],
        'Version': '3'
    },
    MinCount = 1,
    MaxCount = 1,
    NetworkInterfaces=[
        {
            'DeviceIndex': 0,
            'PrivateIpAddresses': [
                {
                    'Primary': True,
                    'PrivateIpAddress': sysinfo['subnet']+str(student_num+3)
                }
            ]
        }
    ]
)

print(response)


interface_response = ec2_client.create_network_interface(
    Description='Student '+str(student_num)+' Internet Interface',
    DryRun=False,
    Groups=[
        sysinfo["group"]
    ],
    PrivateIpAddress=sysinfo['subnet']+str(student_num+19),
    SubnetId=sysinfo['subnet_id'],
    EnablePrimaryIpv6=False
)

response = client.modify_network_interface_attribute(
    #Attachment={
        #'AttachmentId': 'string',
        #'DeleteOnTermination': True|False
    #},
    NetworkInterfaceId=interface_response['NetworkInterface']['NetworkInterfaceId'],
    SourceDestCheck={
        'Value': False
    }
)

print(response)
print(type(response))