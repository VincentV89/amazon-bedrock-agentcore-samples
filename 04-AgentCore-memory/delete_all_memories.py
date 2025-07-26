#!/usr/bin/env python

import boto3
import json
import os

from basic_memory import list_memories
from bedrock_agentcore.memory import MemoryClient


region = os.getenv('AWS_REGION', 'us-west-2')
agentcore_control_client = boto3.client('bedrock-agentcore-control')
memory_client = MemoryClient(region_name=region)


def delete_memory(memory_id: str):
    try:
        response = memory_client.delete_memory(
            memory_id=memory_id
        )
        print(f"Memory '{memory_id}' deleted successfully.")
        print(json.dumps(response, indent=2, default=str))
        return response
    except Exception as e:
        print(f"An error occurred: {e}")


def delete_all_memories():
    memories = list_memories(memory_client)

    for memory in memories:
        memory_id = memory.get('id')
        confirmation = input(
            f"Are you sure you want to delete memory '{memory_id}'? (y/n): "
        )
        if confirmation.lower() != 'y':
            print("Deletion cancelled.")
        else:
            delete_memory(memory.get('id'))


if __name__ == '__main__':
    delete_all_memories()
