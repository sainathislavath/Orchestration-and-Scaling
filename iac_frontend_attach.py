import boto3, base64, json, time

REGION = 'us-west-2'
ACCOUNT_ID = '975050024946'
ECR_FRONTEND_URI = f'{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/sample-frontend:latest'
APP_PORT = 80

ec2 = boto3.client('ec2', region_name=REGION)
elbv2 = boto3.client('elbv2', region_name=REGION)
asg = boto3.client('autoscaling', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)


def find_vpc_alb_sg_subnets():
    vpcs = ec2.describe_vpcs()['Vpcs']
    print("Available VPCs and their tags:")
    for v in vpcs:
        print(v['VpcId'], v.get('Tags', []))

    # Pick VPC tagged with Key='mern' and Value='mern-vpc'
    vpc = [v for v in vpcs if any(t['Key'] == 'mern' and t['Value'] == 'mern-vpc' for t in v.get('Tags', []))]
    if not vpc:
        raise Exception("VPC with tag mern=mern-vpc not found.")
    vpc_id = vpc[0]['VpcId']

    # Get subnets
    subnets = ec2.describe_subnets(Filters=[{'Name':'vpc-id', 'Values':[vpc_id]}])['Subnets']
    subnet_ids = [s['SubnetId'] for s in subnets]

    # If less than 2 subnets in different AZs, create a second subnet
    azs = set(s['AvailabilityZone'] for s in subnets)
    if len(azs) < 2:
        # pick first AZ and create in another AZ
        all_azs = [az['ZoneName'] for az in ec2.describe_availability_zones()['AvailabilityZones']]
        second_az = [az for az in all_azs if az not in azs][0]
        cidr_blocks = ['10.0.2.0/24', '10.0.3.0/24', '10.0.4.0/24']
        new_subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock=cidr_blocks[len(subnets)], AvailabilityZone=second_az)
        subnet_ids.append(new_subnet['Subnet']['SubnetId'])
        print(f"Created second subnet: {new_subnet['Subnet']['SubnetId']}")

    # Security Group: pick first SG with 'backend' in name or description
    sgs = ec2.describe_security_groups(Filters=[{'Name':'vpc-id', 'Values':[vpc_id]}])['SecurityGroups']
    sg_candidates = [s['GroupId'] for s in sgs if 'backend' in s['GroupName'].lower() or 'backend' in s.get('Description', '').lower()]
    if not sg_candidates:
        # create one if not exists
        sg = ec2.create_security_group(
            GroupName='mern-backend-sg',
            Description='Backend SG',
            VpcId=vpc_id
        )
        sg_id = sg['GroupId']
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges':[{'CidrIp':'0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}
            ]
        )
        print(f"Created security group: {sg_id}")
    else:
        sg_id = sg_candidates[0]

    # Ensure Internet Gateway and routes
    ensure_internet_gateway(vpc_id, subnet_ids)

    # Pick ALB named 'mern-alb'
    lbs = elbv2.describe_load_balancers()['LoadBalancers']
    lb = [l for l in lbs if l['LoadBalancerName'] == 'mern-alb']
    if not lb:
        # Create ALB
        lb = elbv2.create_load_balancer(
            Name='mern-alb',
            Subnets=subnet_ids,
            SecurityGroups=[sg_id],
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4'
        )['LoadBalancers'][0]
        print(f"Created ALB: {lb['LoadBalancerArn']}")
    else:
        lb = lb[0]

    return vpc_id, subnet_ids, sg_id, lb


def ensure_internet_gateway(vpc_id, subnets):
    # Check or create IGW
    igws = ec2.describe_internet_gateways(Filters=[{'Name':'attachment.vpc-id', 'Values':[vpc_id]}])['InternetGateways']
    if igws:
        igw_id = igws[0]['InternetGatewayId']
        print(f"Found existing IGW: {igw_id}")
    else:
        igw = ec2.create_internet_gateway()
        igw_id = igw['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        print(f"Created and attached IGW: {igw_id}")

    # Route tables
    rts = ec2.describe_route_tables(Filters=[{'Name':'vpc-id', 'Values':[vpc_id]}])['RouteTables']
    for rt in rts:
        routes = [r.get('DestinationCidrBlock') for r in rt['Routes']]
        if '0.0.0.0/0' not in routes:
            ec2.create_route(RouteTableId=rt['RouteTableId'], DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
            print(f"Added default route in RT {rt['RouteTableId']}")


def ensure_profile():
    try:
        iam.get_instance_profile(InstanceProfileName='EC2SSMInstanceProfile')
        return 'EC2SSMInstanceProfile'
    except:
        raise Exception("Instance profile 'EC2SSMInstanceProfile' not found")


def create_frontend_tg(vpc_id):
    tg = elbv2.create_target_group(
        Name='mern-frontend-tg', Protocol='HTTP', Port=APP_PORT,
        VpcId=vpc_id, TargetType='instance', HealthCheckPath='/'
    )['TargetGroups'][0]
    return tg['TargetGroupArn']


def add_path_routing(lb_arn, backend_tg_arn, frontend_tg_arn):
    listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn)['Listeners']
    http = [l for l in listeners if l['Port'] == 80]
    if not http:
        http = elbv2.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{'Type':'forward', 'TargetGroupArn': frontend_tg_arn}]
        )['Listeners'][0]
    else:
        http = http[0]

    # /api -> backend
    elbv2.create_rule(
        ListenerArn=http['ListenerArn'], Priority=10,
        Conditions=[{'Field':'path-pattern', 'Values':['/api*']}],
        Actions=[{'Type':'forward', 'TargetGroupArn': backend_tg_arn}]
    )

    # default -> frontend
    elbv2.modify_listener(
        ListenerArn=http['ListenerArn'],
        DefaultActions=[{'Type':'forward', 'TargetGroupArn': frontend_tg_arn}]
    )


def create_frontend_lt(sg_id, profile_name):
    user_data = f"""#!/bin/bash
yum update -y
amazon-linux-extras install docker -y || yum install -y docker
systemctl enable docker && systemctl start docker
usermod -aG docker ec2-user
aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com
docker pull {ECR_FRONTEND_URI}
docker run -d --restart=always -p 80:80 --name frontend {ECR_FRONTEND_URI}
"""
    amzn2 = ec2.describe_images(
        Filters=[{'Name':'name', 'Values':['amzn2-ami-hvm-*-x86_64-gp2']},
                 {'Name':'state', 'Values':['available']}],
        Owners=['137112412989'])['Images']
    ami = sorted(amzn2, key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
    lt = ec2.create_launch_template(
        LaunchTemplateName='mern-frontend-lt',
        LaunchTemplateData={
            'ImageId': ami,
            'InstanceType': 't3.micro',
            'IamInstanceProfile': {'Name': profile_name},
            'SecurityGroupIds': [sg_id],
            'UserData': base64.b64encode(user_data.encode()).decode()
        }
    )['LaunchTemplate']
    return lt['LaunchTemplateId']


def create_frontend_asg(lt_id, subnets, tg_arn):
    asg.create_auto_scaling_group(
        AutoScalingGroupName='mern-frontend-asg',
        LaunchTemplate={'LaunchTemplateId': lt_id, 'Version': '$Latest'},
        MinSize=1, MaxSize=3, DesiredCapacity=1,
        VPCZoneIdentifier=",".join(subnets),
        TargetGroupARNs=[tg_arn],
        HealthCheckType='ELB', HealthCheckGracePeriod=60
    )

    
def ensure_backend_tg(vpc_id):
    tgs = elbv2.describe_target_groups()['TargetGroups']
    be_tg = [t for t in tgs if t['TargetGroupName'] == 'mern-backend-tg']
    if be_tg:
        return be_tg[0]['TargetGroupArn']
    
    tg = elbv2.create_target_group(
        Name='mern-backend-tg',
        Protocol='HTTP',
        Port=80,
        VpcId=vpc_id,
        TargetType='instance',
        HealthCheckPath='/'
    )['TargetGroups'][0]
    print(f"Created backend TG: {tg['TargetGroupArn']}")
    return tg['TargetGroupArn']


def main():
    vpc_id, subnets, sg_id, lb = find_vpc_alb_sg_subnets()
    profile = ensure_profile()
    fe_tg_arn = create_frontend_tg(vpc_id)

    # backend TG
    # tgs = elbv2.describe_target_groups()['TargetGroups']
    # be_tg_arn = [t['TargetGroupArn'] for t in tgs if t['TargetGroupName'] == 'mern-backend-tg'][0]
    
    be_tg_arn = ensure_backend_tg(vpc_id)

    add_path_routing(lb['LoadBalancerArn'], be_tg_arn, fe_tg_arn)
    lt_id = create_frontend_lt(sg_id, profile)
    create_frontend_asg(lt_id, subnets, fe_tg_arn)

    print("Frontend attached under '/', backend served under '/api'")
    print("ALB DNS:", lb['DNSName'])


if __name__ == '__main__':
    main()
