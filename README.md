# Orchestration and Scaling

This repository contains the steps, scripts, and infrastructure to deploy a **MERN (MongoDB, Express, React, Node.js)** application on **AWS** using Docker, Boto3, Jenkins, Lambda, EKS, and CloudWatch.

Instead of AWS CodeCommit, we use **GitHub** for version control because CodeCommit is deprecated.

---

## Table of Contents

1. [AWS Environment Setup](#aws-environment-setup)  
2. [Prepare the MERN Application](#prepare-the-mern-application)  
3. [Version Control](#version-control)  
4. [Continuous Integration with Jenkins](#continuous-integration-with-jenkins)  
5. [Infrastructure as Code (IaC) with Boto3](#infrastructure-as-code-iac-with-boto3)  
6. [Deploying Backend Services](#deploying-backend-services)  
7. [Set Up Networking](#set-up-networking)  
8. [Deploying Frontend Services](#deploying-frontend-services)  
9. [AWS Lambda Deployment](#aws-lambda-deployment)  
10. [Kubernetes (EKS) Deployment](#kubernetes-eks-deployment)  
11. [Monitoring and Logging](#monitoring-and-logging)  
12. [Bonus: ChatOps Integration](#bonus-chatops-integration)  

---

## AWS Environment Setup

1. Install AWS CLI and Configure Credentials
    ```bash
    aws configure
    ```
    Set up your access key, secret key, region, and output format.

2. Install Boto3
    ```bash
    pip install boto3
    ```

## Prepare the MERN Application

1. Containerize the Application
    - Create Dockerfiles for the frontend and backend.
    - Ensure dependencies are installed and ports are exposed.
    - Build and run the Dockerfiles.

    ![Build hello service](/images/1.png)
    ![Build profile service](/images/2.png)
    ![Build frontend service](/images/3.png)
    ![Run hello service](/images/4.png)
    ![Run profile service](/images/5.png)
    ![Run frontend service](/images/6.png)

2. Push Docker Images to Amazon ECR
    - Login to AWS ECR using Docker Login
    - Push Docker Image to AWS ECR

    ![Push Hello Service](/images/7.png)
    ![Push Hello Service](/images/8.png)
    ![Push Profile Service](/images/9.png)
    ![Push Profile Service](/images/10.png)
    ![Push Frontend Service](/images/11.png)
    ![Push Frontend Service](/images/12.png)

## Version Control

1. GitHub Repository
    - Create a repository on GitHub.
    - Push your MERN application source code

## Continuous Integration with Jenkins

1. Install Jenkins on EC2
    -Install necessary plugins: Git, Docker, Pipeline.

2. Create Jenkins Jobs
    - Build Docker images and push to ECR.
    - Trigger builds automatically on GitHub commits (webhooks).

    ![Jenkins](/images/13.png)
    ![Jenkins](/images/14.png)
    ![Jenkins](/images/15.png)
    ![Jenkins](/images/16.png)
    ![Jenkins](/images/17.png)

## Infrastructure as Code (IaC) with Boto3

1. Define Infrastructure
    - Use Python scripts with Boto3 to create:
        - VPCs, subnets, and security groups
        - Auto Scaling Groups for backend
        - Elastic Load Balancers (ALB/ELB)
        - EC2 launch templates
    ![VPC](/images/18.png)
    ![VPC](/images/19.png)

## Deploying Backend Services

- Deploy Dockerized backend on EC2 instances within an ASG.
- Ensure containers start automatically with user-data scripts.

## Set Up Networking

1. Create Load Balancer
    - Use Boto3 to create ALB or ELB.
    - Forward `/api` path to backend target group.

2. Configure DNS
    - Use Route 53 or external DNS to point to the ALB.

## Deploying Frontend Services

- Deploy Dockerized frontend on EC2 instances.
- Configure ALB to forward default path `/` to frontend.

![IaC](/images/20.png)

## AWS Lambda Deployment
1. Create Lambda Functions
    - Use Lambda for auxiliary tasks like:
        -MongoDB backups to S3 (timestamped JSON).
        - Triggered on schedules or events.

    ![backup](/images/21.png)

## Kubernetes (EKS) Deployment

1. Create EKS Cluster
    - Install `eksctl` if it is not present in the device.
    ![eksctl](/images/22.png)

    - Run the below command to create the cluster
        ```bash
        eksctl create cluster \
        --name mern-cluster \
        --region us-west-2 \
        --version 1.33 \
        --nodegroup-name mern-nodes \
        --node-type t3.medium \
        --nodes 2 \
        --nodes-min 2 \
        --nodes-max 4 \
        --managed
        ```
    ![cluster](/images/23.png)
    ![cluster](/images/24.png)

2. Deploy Application with Helm
    - Package MERN app using Helm charts.
    - Deploy frontend and backend services on the EKS cluster.
    ![helm](/images/32.png)

## Monitoring and Logging

1. Set Up Monitoring with CloudWatch
    - Create alarms for CPU/Memory usage on nodes.
    - Monitor EKS container insights.
    ![cloudwatch](/images/25.png)
    ![cloudwatch](/images/26.png)

2. Configure Logging
    - Collect logs from applications and Lambda functions.
    - Use CloudWatch Logs or any centralized logging solution.
    ![logs](/images/27.png)
    ![logs](/images/28.png)
    ![logs subscribed](/images/29.png)

## Bonus: ChatOps Integration

1. Create SNS Topics
    - Example: `DeploymentSuccess`, `DeploymentFailure`
    ![SNS](/images/30.png)

2. Lambda for ChatOps
    - Lambda receives deployment events and sends notifications to SNS.

3. Integrate Messaging Platform
    - Connect SNS to Slack, MS Teams, or Telegram.
    - Slack example uses Incoming Webhooks to post notifications.
    ![Slack](/images/31.png)

## References
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [Docker Documentation](https://docs.docker.com/)
- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [Slack Webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)
- [AWS Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

# Author
<p align="center">
  <a href="https://github.com/sainathislavath">
    <img src="https://avatars.githubusercontent.com/u/71361447?v=4&s=40" width="50" style="border-radius:50%;">
    <br>
    <b>Sainath Islavath</b>
  </a>
</p>
