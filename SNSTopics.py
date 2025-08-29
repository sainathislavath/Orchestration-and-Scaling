import boto3

region = 'us-west-2'
sns = boto3.client('sns', region_name=region)

# Create SNS topics for deployment events
success_topic = sns.create_topic(Name='DeploymentSuccess')
failure_topic = sns.create_topic(Name='DeploymentFailure')

print("Success Topic ARN:", success_topic['TopicArn'])
print("Failure Topic ARN:", failure_topic['TopicArn'])
