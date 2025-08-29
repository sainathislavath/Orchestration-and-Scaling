import json
import urllib3

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"
http = urllib3.PoolManager()


def lambda_handler(event, context):
    # SNS sends records in 'Records'
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        deployment = sns_message.get('deployment', 'unknown')
        status = sns_message.get('status', 'failure')

        slack_msg = {
            "text": f"Deployment *{deployment}* finished with status: *{status.upper()}*"
        }

        response = http.request(
            'POST',
            SLACK_WEBHOOK_URL,
            body=json.dumps(slack_msg),
            headers={'Content-Type': 'application/json'}
        )

    return {"statusCode": 200, "body": "Sent to Slack"}
