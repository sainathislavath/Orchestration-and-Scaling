import boto3
import json
import zipfile
import os
import time

REGION = 'us-west-2'
BUCKET_NAME = 'my-mongo-backups-975050'  # Change to a globally unique name
LAMBDA_NAME = 'MongoBackupLambda'
ROLE_NAME = 'MongoBackupLambdaRole'
MONGO_URI = 'mongodb+srv://ContainerOrchestration:ContainerOrchestration@cluster0.juognci.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'  # replace
DB_NAME = 'mydb'

iam = boto3.client('iam', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

# --- 1. Create S3 bucket if it doesn't exist ---
existing_buckets = [b['Name'] for b in s3.list_buckets()['Buckets']]
if BUCKET_NAME not in existing_buckets:
    s3.create_bucket(
        Bucket=BUCKET_NAME,
        CreateBucketConfiguration={'LocationConstraint': REGION}
    )
    print(f"Created bucket: {BUCKET_NAME}")
else:
    print(f"Bucket already exists: {BUCKET_NAME}")

# --- 2. Create IAM role for Lambda ---
assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

try:
    role = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy)
    )
    print(f"Created IAM role: {ROLE_NAME}")
except iam.exceptions.EntityAlreadyExistsException:
    role = iam.get_role(RoleName=ROLE_NAME)
    print(f"IAM role already exists: {ROLE_NAME}")

# Attach S3 full access policy
iam.attach_role_policy(
    RoleName=ROLE_NAME,
    PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
)

# Attach Lambda basic execution role (CloudWatch logs)
iam.attach_role_policy(
    RoleName=ROLE_NAME,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
)

role_arn = role['Role']['Arn']

# --- 3. Prepare Lambda deployment package ---
lambda_code = f"""
import boto3
import json
import datetime
from pymongo import MongoClient

MONGO_URI = '{MONGO_URI}'
S3_BUCKET = '{BUCKET_NAME}'
DB_NAME = '{DB_NAME}'

s3 = boto3.client('s3')

def lambda_handler(event, context):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        docs = list(collection.find({{}}))  # fetch all documents
        for doc in docs:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        json_docs = json.dumps(docs, default=str)
        key = f"{DB_NAME}/{{collection_name}}_{{timestamp}}.json"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json_docs.encode('utf-8'))
        print(f"Backed up {{collection_name}} to s3://{{S3_BUCKET}}/{{key}}")
    return {{'status': 'success'}}
"""

if not os.path.exists('lambda_package'):
    os.makedirs('lambda_package')

with open('lambda_package/lambda_function.py', 'w') as f:
    f.write(lambda_code)

# Zip the code
zipf = zipfile.ZipFile('lambda_package.zip', 'w', zipfile.ZIP_DEFLATED)
zipf.write('lambda_package/lambda_function.py', arcname='lambda_function.py')
zipf.close()

# --- 4. Create or update Lambda function ---
try:
    response = lambda_client.create_function(
        FunctionName=LAMBDA_NAME,
        Runtime='python3.11',
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': open('lambda_package.zip', 'rb').read()},
        Timeout=300,
        MemorySize=128,
    )
    print(f"Created Lambda function: {LAMBDA_NAME}")
except lambda_client.exceptions.ResourceConflictException:
    response = lambda_client.update_function_code(
        FunctionName=LAMBDA_NAME,
        ZipFile=open('lambda_package.zip', 'rb').read()
    )
    print(f"Updated Lambda function code: {LAMBDA_NAME}")

print("Lambda deployment completed successfully!")
