import boto3
import json
import paramiko
from time import sleep


with open("../keys/aws_cli.txt","r") as f:
    keys_str = f.read()

with open("../sysinfo/studentfw.txt","r") as f:
    sysinfo = json.load(f)

with open("../sysinfo/subnets.json","r") as f:
    student_subnets = json.load(f)

with open("../keys/261classpw.txt") as f:
    fw_pw = f.read()

with open("../sysinfo/windows.json","r") as f:
    windows = json.load(f)

keys = keys_str.split("\n")

session = boto3.Session(
    aws_access_key_id=keys[0],
    aws_secret_access_key=keys[1],
    region_name=sysinfo["region"]
)

#build a funciton that modifies the route tables in the VPC
#def modify_routes(student_num, internal, external):


def build_firewall(student_num):
    ec2_client = session.client('ec2')
    instance_response = ec2_client.run_instances(
        LaunchTemplate={
            'LaunchTemplateName': sysinfo['template'],
            'Version': '4'
            },
        MinCount = 1,
        MaxCount = 1,
        NetworkInterfaces=[
            {
                'DeviceIndex': 0,
                'PrivateIpAddresses': [
                    {
                        'Primary': True,
                        'PrivateIpAddress': sysinfo['ext_subnet']+str(student_num+3)
                    }
                ]
            }
        ]
    )

    print("Instance created with ID "+instance_response['Instances'][0]['InstanceId'])


    #Create and attach the external interface
    interface_response = ec2_client.create_network_interface(
        Description='Student '+str(student_num)+' Internet Interface',
        DryRun=False,
        Groups=[
            sysinfo["group"]
        ],
        PrivateIpAddress=sysinfo['ext_subnet']+str(student_num+19),
        SubnetId=sysinfo["subnet_id"],
        EnablePrimaryIpv6=False
    )

    print("Interface created with ID "+interface_response['NetworkInterface']['NetworkInterfaceId'])

    con = True
    while con:
        try:
            attach_response = ec2_client.attach_network_interface(
                DeviceIndex=1,
                DryRun=False,
                InstanceId=instance_response['Instances'][0]['InstanceId'],
                NetworkInterfaceId=interface_response['NetworkInterface']['NetworkInterfaceId']
            )
            con = False
        except:
            print("Not running yet")
            sleep(10)

    print("External data interface attached to instance")

    modify_response = ec2_client.modify_network_interface_attribute(
        #Attachment={
        #    'AttachmentId': attach_response['AttachmentId'],
        #    'DeleteOnTermination': True
        #},
        NetworkInterfaceId=interface_response['NetworkInterface']['NetworkInterfaceId'],
        SourceDestCheck={
            'Value': False
        }
    )

    print("Source/destination check removed") #and delete on termination enabled")

    #Create and attach the internal interface
    interface_response_int = ec2_client.create_network_interface(
        Description='Student '+str(student_num)+' Private Interface',
        DryRun=False,
        Groups=[
            sysinfo["group"]
        ],
        PrivateIpAddress=sysinfo['int_subnet']+str((student_num-1)*16+4),
        SubnetId=student_subnets[str(student_num)],
        EnablePrimaryIpv6=False
    )

    print("Interface created with ID "+interface_response['NetworkInterface']['NetworkInterfaceId'])

    
    attach_response = ec2_client.attach_network_interface(
        DeviceIndex=2,
        DryRun=False,
        InstanceId=instance_response['Instances'][0]['InstanceId'],
        NetworkInterfaceId=interface_response_int['NetworkInterface']['NetworkInterfaceId']
    )

    print("Internal data interface attached to instance")

    modify_response = ec2_client.modify_network_interface_attribute(
        #Attachment={
        #    'AttachmentId': attach_response['AttachmentId'],
        #    'DeleteOnTermination': True
        #},
        NetworkInterfaceId=interface_response_int['NetworkInterface']['NetworkInterfaceId'],
        SourceDestCheck={
            'Value': False
        }
    )

    print("Source/destination check removed") #and delete on termination enabled")

def change_password(student_num):
    k = paramiko.RSAKey.from_private_key_file("../keys/student-subnet-ssh.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connecting")
    c.connect( hostname = sysinfo['ext_subnet']+str(student_num+3), username = "admin", pkey = k )
    print("connected")
    commands = ["configure","set mgt-config users admin password",fw_pw,fw_pw,"commit"]
    for command in commands:
        _stdin, _stdout,_stderr = c.exec_command(command)
        print("Output",_stdout.read().decode())
        print("Errors",_stderr.read().decode())
    _stdin.close()

def build_windows(student_num):
    ec2_client = session.client('ec2')
    instance_response = ec2_client.run_instances(
        LaunchTemplate={
            'LaunchTemplateName': windows['template'],
            'Version': '1'
            },
        MinCount = 1,
        MaxCount = 1,
        NetworkInterfaces=[
            {
                'SubnetId': student_subnets[str(student_num)],
                'DeviceIndex': 0,
                'PrivateIpAddresses': [
                    {
                        'Primary': True,
                        'PrivateIpAddress': sysinfo['int_subnet']+str((student_num-1)*16+5)
                    }
                ]
            }
        ]
    )

def build_linux(student_num):
    ec2_client = session.client('ec2')
    instance_response = ec2_client.run_instances(
        LaunchTemplate={
            'LaunchTemplateName': "Student-Net-RHEL-NGINX",
            'Version': '3'
            },
        MinCount = 1,
        MaxCount = 1,
        NetworkInterfaces=[
            {
                'SubnetId': student_subnets[str(student_num)],
                'DeviceIndex': 0,
                'PrivateIpAddresses': [
                    {
                        'Primary': True,
                        'PrivateIpAddress': sysinfo['int_subnet']+str((student_num-1)*16+6)
                    },
                ],
                'Groups': [
                    'sg-0066bd253d415296e'
                    ]
            }
        ]
    )

my_student_num = 1

#change_password(my_student_num)

#build_linux(my_student_num)

for i in range(2,17):
    build_linux(i)
    print("Build linux box number",i)
