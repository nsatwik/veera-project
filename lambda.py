import boto3
import os
import time
from datetime import datetime

ebs_client = boto3.client('elasticbeanstalk')

APP_NAME = "Test-Task"   ##Your own EBS APP Name
ENV_NAME = "Test-Task-env"  ##Your Own EBS Env Name

def wait_for_environment_ready(env_name, max_retries=30):
    """Wait until Elastic Beanstalk environment is Ready."""
    for _ in range(max_retries):
        env_info = ebs_client.describe_environments(EnvironmentNames=[env_name])['Environments'][0]
        status = env_info['Status']
        print(f"Environment status: {status}")
        if status == "Ready":
            return True
        time.sleep(10)  # wait before checking again
    return False

def lambda_handler(event, context):
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        base_label = os.path.basename(key).replace(".", "_").replace("/", "_")
        version_label = f"{base_label}_{timestamp}"

        print(f"📦 New file detected: {bucket}/{key}")
        print(f"🚀 Deploying version: {version_label}")

        # Step 1: Create new application version
        ebs_client.create_application_version(
            ApplicationName=APP_NAME,
            VersionLabel=version_label,
            SourceBundle={'S3Bucket': bucket, 'S3Key': key},
            Process=True
        )

        # Step 2: Wait for environment to be ready
        if not wait_for_environment_ready(ENV_NAME):
            raise RuntimeError("Environment did not become ready in time.")

        # Step 3: Deploy version
        ebs_client.update_environment(
            EnvironmentName=ENV_NAME,
            VersionLabel=version_label
        )

        print(f"✅ Deployment successful: {version_label} → {ENV_NAME}")
        return {"statusCode": 200, "body": f"Deployed {version_label} to {ENV_NAME}"}

    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return {"statusCode": 500, "body": f"Deployment failed: {str(e)}"}
