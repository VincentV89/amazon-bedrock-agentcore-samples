# Agent Deployment - Strands Agent Infrastructure Deployment with AgentCore

This tutorial guides you through deploying the Strands Agent for a Data Analyst Assistant for Video Game Sales using Amazon Bedrock AgentCore.

## Overview

You will deploy the following AWS services:

**Amazon Bedrock AgentCore** is a fully managed service that enables you to deploy, run, and scale your custom agent applications with built-in runtime and memory capabilities.

- **AgentCore Runtime**: Provides a managed execution environment with invocation endpoints (`/invocations`) and health monitoring (`/ping`) for your agent instances
- **AgentCore Memory**: A fully managed service that gives AI agents the ability to remember, learn, and evolve through interactions by capturing events, transforming them into memories, and retrieving relevant context when needed

The AgentCore infrastructure handles all storage complexity and provides efficient retrieval without requiring developers to manage underlying infrastructure, ensuring continuity and traceability across agent interactions.

> [!IMPORTANT]
> This sample application is intended for demo purposes and is not production-ready. Please validate the code according to your organization's security best practices.
>
> Remember to clean up resources after testing to avoid unnecessary costs by following the cleanup steps provided.

## Prerequisites

Before you begin, ensure you have:

* Installed AgentCore with the following command:

```bash
pip install bedrock-agentcore
```

## Deploy the Strands Agent with Amazon Bedrock AgentCore

1. Navigate to the CDK project folder (`agentcore-strands-data-analyst-assistant`).

2. Configure the AgentCore deployment:

```bash
agentcore configure --entrypoint app.py --name agentcoredataanalystassistant -er $AGENT_CORE_ROLE_EXECUTION
```

   Use the default values when prompted.

3. Deploy the infrastructure stack to AWS:

```bash
agentcore launch
```

## Test the Agent

You can test your agent by invoking the AgentCore commands:

```bash
agentcore invoke '{"prompt": "Hello world!", "session_id": "c5b8f1e4-9a2d-4c7f-8e1b-5a9c3f6d2e8a", "prompt_uuid": "4e7a8b5c-2f9d-6e3a-8b4c-5d6e7f8a9b0c"}'

agentcore invoke '{"prompt": "What is the structure of your available data?", "session_id": "c5b8f1e4-9a2d-4c7f-8e1b-5a9c3f6d2e8a", "prompt_uuid": "9f2e8d7c-4a3b-1e5f-6a7b-8c9d0e1f2a3b"}'

agentcore invoke '{"prompt": "Which developers tend to get the best reviews?", "session_id": "c5b8f1e4-9a2d-4c7f-8e1b-5a9c3f6d2e8a", "prompt_uuid": "1c5e9a3f-7b2d-4e8c-6a9b-0d1e2f3a4b5c"}'

agentcore invoke '{"prompt": "Give me a summary of our conversation", "session_id": "c5b8f1e4-9a2d-4c7f-8e1b-5a9c3f6d2e8a", "prompt_uuid": "6b8e4d2a-9c7f-3e5b-1a4d-8f9e0c1b2a3d"}'
```

## Cleaning Up Resources (Optional)

To avoid unnecessary charges, delete the agent resources:

```bash
agentcore destroy
```

## Thank You

Thank you for following this tutorial. If you have any questions or feedback, please refer to the Amazon Bedrock AgentCore documentation.

## License

This project is licensed under the Apache-2.0 License.