#!/usr/bin/env python

"""
Browser automation script using Amazon Bedrock AgentCore and Nova Act.

This script enables AI-powered web automation by leveraging Amazon Bedrock AgentCore 
and Nova Act to perform browser-based tasks using natural language instructions.

Features:
- Initializes a browser session through Amazon Bedrock AgentCore's browser tool
- Connects to Nova Act for natural language web interactions and automation
- Performs automated web navigation, searches and data extraction
- Supports custom prompts and starting URLs via command line arguments

Required Environment Variables:
    NOVA_ACT_API_KEY: API key for Nova Act service

Usage:
    python script.py --prompt "search instruction" --starting-page "https://example.com"

Dependencies:
    - boto3
    - bedrock-agentcore
    - nova-act
    - rich

Acknowledgements:
    This code has been adapted from:
    - Amazon Bedrock AgentCore documentation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-building-agents.html
    - Amazon Bedrock AgentCore samples repository: https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/05-AgentCore-tools/02-Agent-Core-browser-tool/01-browser-with-NovaAct/01_getting_started-agentcore-browser-tool-with-nova-act.ipynb
"""

import argparse
import json
import os

from boto3.session import Session
from bedrock_agentcore.tools.browser_client import browser_session
from nova_act import NovaAct
from rich.console import Console

console = Console()

boto_session = Session()
region = boto_session.region_name
print(f'Using AWS region {region}')

NOVA_ACT_API_KEY = os.getenv('NOVA_ACT_API_KEY', None)
if not NOVA_ACT_API_KEY:
    raise Exception('Please set the NOVA_ACT_API_KEY environment variable (export NOVA_ACT_API_KEY="..." before running this script')


def browser_with_nova_act(prompt: str, starting_page: str, region: str):
    """
    Initialize a browser session and execute a Nova Act automation task.

    Args:
        prompt (str): The natural language instruction for Nova Act to execute
        starting_page (str): The URL where the browser session should start
        region (str): AWS region for the browser session

    Returns:
        NovaActResult: Result object containing the automation execution response

    Raises:
        Exception: If there is an error during Nova Act execution
    """
    with browser_session(region) as client:
        ws_url, headers = client.generate_ws_headers()
        try:
            with NovaAct(
                cdp_endpoint_url=ws_url,
                cdp_headers=headers,
                preview={"playwright_actuation": True},
                nova_act_api_key=NOVA_ACT_API_KEY,
                starting_page=starting_page,
            ) as nova_act:
                result = nova_act.act(prompt)
        except Exception as e:
            console.print(f"NovaAct error: {e}")
        return result


def main(args):
    result = browser_with_nova_act(
        prompt = args.prompt,
        starting_page = args.starting_page,
        region = region
    )
    console.print(f"\n[cyan] Response[/cyan] {result.response}")
    console.print(f"\n[bold green]Nova Act Result:[/bold green] {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="Browser Search instruction")
    parser.add_argument("--starting-page", required=True, help="Starting URL")
    args = parser.parse_args()
    main(args)
