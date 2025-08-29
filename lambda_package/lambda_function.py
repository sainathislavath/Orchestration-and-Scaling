
import boto3
import json
import datetime
from pymongo import MongoClient

MONGO_URI = 'mongodb+srv://ContainerOrchestration:ContainerOrchestration@cluster0.juognci.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
S3_BUCKET = 'my-mongo-backups-975050'
DB_NAME = 'mydb'

s3 = boto3.client('s3')

def lambda_handler(event, context):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        docs = list(collection.find({}))  # fetch all documents
        for doc in docs:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        json_docs = json.dumps(docs, default=str)
        key = f"mydb/{collection_name}_{timestamp}.json"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json_docs.encode('utf-8'))
        print(f"Backed up {collection_name} to s3://{S3_BUCKET}/{key}")
    return {'status': 'success'}
