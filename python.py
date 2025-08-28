import boto3
import botocore
import time

# --- Clients ---
ec2_client = boto3.client('ec2', region_name='us-west-2')
autoscaling_client = boto3.client('autoscaling', region_name='us-west-2')
lambda_client = boto3.client('lambda', region_name='us-west-2')
iam_client = boto3.client('iam', region_name='us-west-2')

# --- 1. Create VPC ---
vpc = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
vpc_id = vpc['Vpc']['VpcId']
ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
print(f"VPC created: {vpc_id}")

# --- 2. Create Subnet ---
subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-west-2a')
subnet_id = subnet['Subnet']['SubnetId']
print(f"Subnet created: {subnet_id}")

# --- 3. Create Security Group ---
sg = ec2_client.create_security_group(
    GroupName='backend-sg',
    Description='Security group for backend instances',
    VpcId=vpc_id
)
sg_id = sg['GroupId']
# Allow HTTP & SSH
ec2_client.authorize_security_group_ingress(
    GroupId=sg_id,
    IpPermissions=[
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
         'IpRanges':[{'CidrIp':'0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 3000, 'ToPort': 3000,
         'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}
    ]
)
print(f"Security group created: {sg_id}")

# --- 4. Launch Configuration for ASG ---
lc_name = f"backend-lc-{int(time.time())}" 
autoscaling_client.create_launch_configuration(
    LaunchConfigurationName=lc_name,
    ImageId='ami-08d70e59c07c61a3a',  # Replace with a valid AMI
    InstanceType='t2.micro',
    SecurityGroups=[sg_id],
    KeyName='sainath'  # Replace with your EC2 key pair
)
print(f"Launch configuration created: {lc_name}")

# --- 5. Create Auto Scaling Group ---
asg_name = 'backend-asg'

# Check if ASG exists
existing_asgs = autoscaling_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])['AutoScalingGroups']
if existing_asgs:
    print(f"Auto Scaling Group already exists: {asg_name}")
else:
    autoscaling_client.create_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchConfigurationName=lc_name,
        MinSize=1,
        MaxSize=3,
        DesiredCapacity=1,
        VPCZoneIdentifier=subnet_id
    )
    print(f"Auto Scaling Group created: {asg_name}")

# --- 6. Optional: Create Lambda Function ---
role_name = 'lambda-execution-role'

# Check if role exists
try:
    role = iam_client.get_role(RoleName=role_name)
    role_arn = role['Role']['Arn']
    print(f"Using existing IAM role: {role_arn}")
except iam_client.exceptions.NoSuchEntityException:
    # Create role if it doesn't exist
    role = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument='''{
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": "lambda.amazonaws.com"
              },
              "Action": "sts:AssumeRole"
            }
          ]
        }'''
    )
    role_arn = role['Role']['Arn']
    # Attach basic execution policy
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )
    print(f"Created IAM role: {role_arn}")

# Create Lambda function
with open('lambda_function.zip', 'rb') as f:
    zipped_code = f.read()

lambda_client.create_function(
    FunctionName='MyLambdaFunction',
    Runtime='python3.11',
    Role=role_arn,
    Handler='lambda_function.lambda_handler',
    Code={'ZipFile': zipped_code},
    Timeout=30,
    MemorySize=128
)
print("Lambda function created successfully")
