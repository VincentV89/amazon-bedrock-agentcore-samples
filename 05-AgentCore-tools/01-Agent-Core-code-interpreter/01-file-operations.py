#!/usr/bin/env python

"""
A script for executing Python code in a secure sandbox environment using Amazon Bedrock's Code Interpreter.

This script provides functionality to:
1. Upload local files to a secure sandbox environment
2. Execute Python code within that sandbox
3. Retrieve and display execution results

The script uses Amazon Bedrock's Code Interpreter to create an isolated execution environment,
making it safe to run untrusted code or perform file operations. It supports uploading multiple
files from a local directory and executing a specified Python script against those files.

Key Features:
- Secure file operations in an isolated sandbox
- Support for uploading multiple file types (default: .csv and .py)
- Error handling for file operations
- Clean sandbox environment for each execution
- Automatic resource cleanup

Requirements:
- AWS credentials configured
- bedrock-agentcore package installed
- Access to Amazon Bedrock service

Acknowledgements - This code has been adapted from:
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-file-operations.html
- https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/05-AgentCore-tools/01-Agent-Core-code-interpreter/01-file-operations-using-code-interpreter

"""

import json
import os

from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from typing import Dict, Any, List


# Initialize the Code Interpreter with your AWS region
# This creates a secure sandbox environment for code execution
code_client = CodeInterpreter('us-west-2')
code_client.start()


def read_file(file_path: str) -> str:
    """Read file content from local filesystem with error handling.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        str: File content as string, empty string if error occurs
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return ""
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""


def call_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Invoke Code Interpreter sandbox tools and return results.
    
    Args:
        tool_name (str): Name of the sandbox tool to invoke (e.g., 'writeFiles', 'executeCode')
        arguments (Dict[str, Any]): Tool-specific arguments
        
    Returns:
        str: JSON-formatted result from the tool execution
    """
    response = code_client.invoke(tool_name, arguments)
    # Extract the first result from the streaming response
    for event in response["stream"]:
        return json.dumps(event["result"])


def upload_files_to_sandbox(folder: str, extensions: List[str] = ['csv', 'py'] ):
    """Uploads files from a local folder to the sandbox environment.
    
    Args:
        folder (str): Path to the local folder containing files to upload
        
    Returns:
        List[Dict[str, str]]: List of dictionaries containing file information
                              Each dictionary has 'path' (filename) and 'text' (content) keys
        
    The function reads all files from the specified folder and uploads them to
    the secure sandbox environment using the writeFiles tool. Each file is
    uploaded with its original filename and content.
    
    The files are uploaded to the sandbox and a list of the file information is returned
    for further processing. The actual upload result is printed but not returned.
    """

    # Get list of all files in the folder
    files_to_create = []
    for filename in os.listdir(folder):
        if os.path.splitext(filename)[1].lower().lstrip('.') not in extensions:        
            continue
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            file_content = read_file(file_path)
            files_to_create.append({
                "path": filename,
                "text": file_content
            })

    # Upload files to the secure sandbox environment 
    writing_files = call_tool("writeFiles", {"content": files_to_create})
    print('Writing files result:')
    print(json.dumps(json.loads(writing_files), indent=2))
    return files_to_create


def read_sandbox_files():
    """Lists all files currently in the sandbox environment.
    
    Returns:
        str: JSON-formatted string containing the list of files in the sandbox
        
    This function verifies the files were successfully created by calling the
    listFiles tool on the root path of the sandbox environment.
    """
    return call_tool("listFiles", {"path": ""})


def execute_script_in_sandbox(folder: str, python_script: str):
    """Execute a Python script in a secure sandbox environment with uploaded files.
    
    This function performs the following steps:
    1. Uploads files from a specified folder to the Code Sandbox
    2. Verifies the uploaded files in the sandbox
    3. Executes the specified Python script in the sandbox
    4. Displays execution results and standard output
    5. Cleans up sandbox resources
    
    Args:
        folder (str): Path to local folder containing files to upload
        python_script (str): Name of the Python script file to execute
        
    Raises:
        ValueError: If the specified Python script is not found in the uploaded files
        
    Returns:
        None: Results are printed to standard output
    """

    # Step 1: Upload files to Code Sandbox
    files_to_create = upload_files_to_sandbox(folder)

    # Step 2: Verify files that were uploaded to Code Sandbox
    listing_files = read_sandbox_files()
    print("\nFiles in sandbox:")
    print(json.dumps(json.loads(listing_files), indent=2))

    # Step 3: Execute the Python analysis script in the sandbox
    python_code = [ file['text'] for file in files_to_create if file['path'] == python_script ]
    if not len(python_code):
        raise ValueError(f'Python script not found: {python_script}')

    code_execute_result = call_tool("executeCode", {
        "code": python_code[0],
        "language": "python",
        "clearContext": True  # Set to true to ensure clean execution environment
    })

    # Step 4: Parse execution results and display output
    analysis_results = json.loads(code_execute_result)
    print(f"Full analysis results:\n{json.dumps(analysis_results, indent=2)}")

    print("\nStandard output from analysis:")
    print(analysis_results['structuredContent']['stdout'])

    # Step 5: Clean up: stop the Code Interpreter session
    code_client.stop()  # release sandbox resources
    print("\nCode Interpreter session stopped successfully!")


if __name__ == '__main__':
    execute_script_in_sandbox(
        folder = '01-file-operations-using-code-interpreter/samples',
        python_script = 'stats.py'
    )
