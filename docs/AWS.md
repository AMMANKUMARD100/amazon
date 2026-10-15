# CampusMate AI – AWS Hosting & Production Deployment Guide

This guide details how to configure, secure, and deploy **CampusMate AI** on Amazon Web Services (AWS), utilizing **Amazon Bedrock** for intelligent conversational reasoning and scalable cloud hosting architectures.

---

## 1. Amazon Bedrock Setup

CampusMate AI utilizes Amazon Bedrock's native **Converse API** (`boto3 bedrock-runtime`) for structured tool-calling, agentic multi-step reasoning, and voice-ready natural language generation.

### 1.1 Enable Model Access in AWS Bedrock Console
1. Log in to the [AWS Management Console](https://console.aws.amazon.com/bedrock/).
2. Select your desired AWS Region (e.g., `us-east-1` (N. Virginia) or `us-west-2` (Oregon)).
3. In the left navigation sidebar, scroll down to **Bedrock Configurations** and click **Model access**.
4. Click **Modify model access** or **Enable specific models**.
5. Locate **Anthropic**:
   - Check **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) – *Recommended for low-latency, cost-effective voice interactions.*
   - Check **Claude 3.5 Sonnet** (`anthropic.claude-3-5-sonnet-20240620-v1:0` or v2) – *Optional for advanced complex reasoning.*
6. Click **Next**, review the use case agreement, and click **Submit**. Access is typically granted within 1–2 minutes.

### 1.2 IAM Policy & Least-Privilege Permissions
To allow the CampusMate AI application to communicate with Amazon Bedrock, attach the following least-privilege IAM policy to the EC2 instance profile, ECS task execution role, or Lambda execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockConverse",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
      ]
    }
  ]
}
```

---

## 2. Configuration & Environment Variables

CampusMate AI is fully configured via environment variables.

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `demo` | Set to `bedrock` to activate live Amazon Bedrock Converse API. Set to `demo` for offline deterministic fallback. |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | The Bedrock Foundation Model ID to invoke. |
| `AWS_REGION` | `us-east-1` | AWS region where Bedrock model access is active. |
| `AWS_ACCESS_KEY_ID` | *(Optional)* | Only required for local dev outside AWS. In production, use IAM Roles. |
| `AWS_SECRET_ACCESS_KEY` | *(Optional)* | Only required for local dev outside AWS. In production, use IAM Roles. |
| `SECRET_KEY` | `dev_secret_key_...` | Flask session cryptographic key. Must be a secure 32+ character string in production. |
| `DATABASE_PATH` | `backend/database/campusmate.db` | Absolute or relative path to SQLite database file, or mounted persistent volume. |
| `PORT` | `5000` | Port for the core Flask REST API server. |
| `MCP_PORT` | `8000` | Port for the FastMCP Streamable-HTTP server. |

---

## 3. Production Hosting Architecture Options

### Option A: Amazon EC2 with Docker Compose (Recommended for Simplicity)
Ideal for small-to-medium university deployments with straightforward operations.

* **Recommended Instance:** `t4g.small` (2 vCPU, 2 GB RAM, ARM-based Graviton2) or `t3.medium` (2 vCPU, 4 GB RAM, x86).
* **Setup Steps:**
  1. Launch an Amazon Linux 2023 or Ubuntu 24.04 LTS instance with an attached IAM Role possessing the Bedrock policy.
  2. Install Docker and Docker Compose:
     ```bash
     sudo dnf install -y docker git
     sudo systemctl enable --now docker
     sudo usermod -aG docker ec2-user
     ```
  3. Clone the repository and configure `.env`:
     ```bash
     git clone https://github.com/your-org/campusmate-ai.git /opt/campusmate
     cd /opt/campusmate
     echo "LLM_PROVIDER=bedrock" >> .env
     echo "AWS_REGION=us-east-1" >> .env
     echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
     ```
  4. Launch containers via Docker Compose:
     ```bash
     docker compose -f docker-compose.yml up -d --build
     ```
  5. Setup Nginx as a reverse proxy with Let's Encrypt SSL terminating on port 443 and proxying traffic to port 3000 (React Frontend) and port 5000 (Flask Backend).

---

### Option B: Amazon ECS on AWS Fargate (Serverless Container Architecture)
Recommended for enterprise university IT environments requiring high availability, auto-scaling, and zero EC2 server management.

```text
+---------------------------------------------------------------------------------+
|                       AWS CLOUD (VPC - Multi-AZ)                                |
|                                                                                 |
|  +--------------------+                                                         |
|  | AWS Route 53 (DNS) |                                                         |
|  +---------+----------+                                                         |
|            |                                                                    |
|            v                                                                    |
|  +---------------------------------------------------------------------------+  |
|  |                 Application Load Balancer (ALB) - HTTPS 443               |  |
|  +----+----------------------------------+------------------------------+----+  |
|       | Path: /*                         | Path: /api/*                 |       |
|       v                                  v                              v       |
|  +--------------------+          +--------------------+          +-----------+  |
|  | ECS Task: Frontend |          | ECS Task: Backend  |          | ECS Task: |  |
|  | Nginx / Vite React |          | Flask REST API     |          | FastMCP   |  |
|  +--------------------+          +---------+----------+          +-----+-----+  |
|                                            |                           |        |
|                                            +-------------+-------------+        |
|                                                          |                      |
|                                                          v                      |
|                                            +---------------------------+        |
|                                            | Amazon EFS (Shared DB)    |        |
|                                            | or Amazon RDS Aurora      |        |
|                                            +---------------------------+        |
+----------------------------------------------------------+----------------------+
                                                           | IAM Role
                                                           v
                                             +---------------------------+
                                             | Amazon Bedrock (Converse) |
                                             +---------------------------+
```

* **Components:**
  - **Task 1 (Frontend):** React static build served by lightweight Alpine Nginx container (0.25 vCPU, 0.5 GB RAM).
  - **Task 2 (Backend):** Flask REST API application with Gunicorn production WSGI runner (0.5 vCPU, 1 GB RAM).
  - **Task 3 (MCP Server):** FastMCP Streamable-HTTP container (0.25 vCPU, 0.5 GB RAM).
  - **Storage:** Amazon EFS persistent volume mounted for SQLite, or seamless migration to Amazon Aurora PostgreSQL Serverless v2.
  - **IAM:** Task Execution Role attached directly to ECS Tasks granting `bedrock:InvokeModel`.

---

### Option C: AWS Lambda + Amazon API Gateway (Pure Serverless)
For low-maintenance, scale-to-zero serverless deployments:
* Wrap Flask with `aws-wsgi` or **AWS Lambda Web Adapter** (`public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4`).
* Configure API Gateway HTTP API ($1.00/million requests) with binary media types enabled.
* Connect database to **Amazon Aurora Serverless v2 (PostgreSQL)** via Data API, or attach **Amazon EFS for Lambda** for the SQLite file.
* Concurrency limit prevents runaway costs while providing instant response elasticity during exam peak hours.

---

## 4. Cost Estimation (Monthly Budget)

Below is an estimated monthly cost for an active cohort of **500 university students** generating approximately **20,000 conversational voice queries and tool invocations per month**:

| Service / Resource | Specifications & Usage | Estimated Monthly Cost (USD) |
| :--- | :--- | :---: |
| **Amazon Bedrock (Claude 3 Haiku)** | 20,000 queries $\times$ avg. 800 input tokens = 16M tokens ($0.25 / 1M)<br>20,000 queries $\times$ avg. 150 output tokens = 3M tokens ($1.25 / 1M) | $4.00<br>$3.75 |
| **Compute: Amazon EC2 (`t4g.small`)** | 1 instance $\times$ 730 hours ($0.0168/hour) running Docker | $12.26 |
| **Amazon EBS Storage** | 20 GB General Purpose gp3 root volume | $1.60 |
| **Data Transfer & Networking** | Under 15 GB outbound internet data per month | $1.35 |
| **AWS Certificate Manager & Route 53** | 1 Hosted Zone + Free Public SSL/TLS Certificates | $0.50 |
| **Total Estimated Monthly Cost** | *Full Production Stack for 500 Students* | **~$23.46 / month** |

> [!TIP]
> Under the **AWS Free Tier** (first 12 months for new accounts), the `t4g.small` instance is eligible for free trial hours in select regions, reducing the total operational cost to **under $8.00 / month** solely for Bedrock token usage.

---

## 5. Security & Production Checklist

- [x] **Enforce HTTPS:** Ensure all browser audio (Web Speech API) and REST traffic runs over TLS 1.3. Web Speech API voice capture is blocked by modern browsers on insecure HTTP origins (except localhost).
- [x] **Rotate Secret Keys:** Replace the default Flask `SECRET_KEY` with a cryptographically secure 256-bit random key (`python -c "import secrets; print(secrets.token_hex(32))"`).
- [x] **Disable Flask Debug Mode:** Ensure `debug=False` in production `backend/app.py`. Use Gunicorn (`gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app`).
- [x] **Database Backups:** Schedule an automated daily cron job or AWS Backup plan to snapshot `campusmate.db` or Amazon RDS volumes.
- [x] **Rate Limiting:** Protect public endpoints against DDoS with the built-in sliding-window limiter or an AWS WAF Web ACL on your Application Load Balancer.
