pipeline {
    agent any

    environment {
        AWS_ACCOUNT_ID = '975050024946'             // Your AWS Account ID
        AWS_REGION = 'us-west-2'                    // Your AWS region
        ECR_CREDENTIALS = 'aws-creds'              // Jenkins credentials ID for AWS (Access Key + Secret)
        HELLO_IMAGE = "hello-service"
        PROFILE_IMAGE = "profile-service"
        FRONTEND_IMAGE = "sample-frontend"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/YourGitHubUsername/YourRepo.git'
            }
        }

        stage('Login to AWS ECR') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${ECR_CREDENTIALS}", 
                                                 usernameVariable: 'AWS_ACCESS_KEY_ID', 
                                                 passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    sh '''
                        aws ecr get-login-password --region $AWS_REGION | \
                        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
                    '''
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                sh '''
                    # Build hello-service
                    docker build -t hello-service:latest ./backend/helloService
                    
                    # Build profile-service
                    docker build -t profile-service:latest ./backend/profileService
                    
                    # Build frontend
                    docker build -t sample-frontend:latest ./frontend
                '''
            }
        }

        stage('Tag Docker Images for ECR') {
            steps {
                sh '''
                    docker tag hello-service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hello-service:latest
                    docker tag profile-service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/profile-service:latest
                    docker tag sample-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sample-frontend:latest
                '''
            }
        }

        stage('Push Docker Images to ECR') {
            steps {
                sh '''
                    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hello-service:latest
                    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/profile-service:latest
                    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sample-frontend:latest
                '''
            }
        }
    }

    post {
        success {
            echo 'All images built and pushed successfully!'
        }
        failure {
            echo 'Build or push failed. Check the logs!'
        }
    }
}
