import boto3
import json
import os


region = os.getenv('AWS_REGION', 'us-west-2')
iam_client = boto3.client('iam')

agent_arn = os.getenv('AGENTCORE_ROLE_ARN', None)
if agent_arn is None:
    try:
        response = iam_client.get_role(RoleName='agentcore-strands_claude-role')
        AGENTCORE_ROLE_ARN = response['Role']['Arn']
        print(f"Role ARN: {AGENTCORE_ROLE_ARN}")
    except Exception as e:
        raise ValueError(f"Error getting role ARN: {e}. AGENTCORE_ROLE_ARN environment variable is not set.")

agentcore_client = boto3.client(
    'bedrock-agentcore',
    region_name=region
)

boto3_response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    qualifier="DEFAULT",
    payload=json.dumps({"prompt": "What is 111,111,111 times 111,111,111?"})
)
if "text/event-stream" in boto3_response.get("contentType", ""):
    content = []
    for line in boto3_response["response"].iter_lines(chunk_size=1):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                logger.info(line)
                content.append(line)
    display(Markdown("\n".join(content)))
else:
    try:
        events = []
        for event in boto3_response.get("response", []):
            events.append(event)
    except Exception as e:
        events = [f"Error reading EventStream: {e}"]
    display(Markdown(json.loads(events[0].decode("utf-8"))))
