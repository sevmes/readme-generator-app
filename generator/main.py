#!/usr/bin/python
import os
import sys
import threading
import json
import string
import random
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import git
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting

if len(sys.argv) < 3:
    print("Usage: python main.py <PROJECT_ID> <LOCATION>")
    sys.exit(1)

# Project and location settings for Vertex AI
PROJECT_ID = sys.argv[1]
LOCATION = sys.argv[2]
MODEL_NAME = "gemini-1.5-pro-002"
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Configuration for text generation
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 0.95,
}

# Safety settings for the model
SAFETY_SETTINGS = [
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE),
]

# Excluded directories and file extensions for code analysis
EXCLUDED_DIRECTORIES = [".git", "genproto", ".venv", "node_modules", "dist", "build", "tests", "test", "bin", "target", "out", ".next"]


def get_code_file_extensions(directory):
    """Identifies code file extensions within a directory using Gemini."""

    found_extensions = {os.path.splitext(filename)[1][1:] for root, _, filenames in os.walk(directory) for filename in filenames}

    prompt = f"""
    Please return a list of extensions that identify files containing source code.
    The format should be a list of extension separated by commas. Your response should only
    be the list of extension, or ".c" if no extension in the original list is an extension of source code file.
    Example input : 
    csv,ts,jpg,cpp,java
    Output :
    ts,c,cpp,java

    Here is the input :
    {",".join(found_extensions)}
    """

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(MODEL_NAME)
    chat = model.start_chat()
    response = chat.send_message(prompt)
    print(f"Code extensions found : {response.text}")

    return_value = response.text.split(",")
    if "md" in return_value:
        return_value.remove("md")
    return return_value


def read_code_files(directory, allowed_extensions):
    """Reads code files from the specified directory, excluding specified subdirectories."""

    code_files = {}
    for root, _, filenames in os.walk(directory):
        # Load .gitignore for the current directory and its parents
        gitignore_entries = []
        current_dir = root
        while current_dir != "/":
            gitignore_path = os.path.join(current_dir, ".gitignore")
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as f:
                    gitignore_entries.extend(f.read().splitlines())
            current_dir = os.path.dirname(current_dir)
        
        for filename in filenames:
            if not any(filename.endswith(ext) for ext in allowed_extensions):
                continue

            filepath = os.path.join(root, filename)

            # Check if file path should be ignored based on .gitignore
            if any(f"/{entry.strip()}/" in filepath for entry in gitignore_entries):
                print(f"Skipping ignored file: {filepath}")
                continue
            
            if any(f"/{subdir}/" in filepath for subdir in EXCLUDED_DIRECTORIES):
                continue

            print(f"Reading file: {filepath}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    code_files[os.path.relpath(filepath)] = [content]
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")
    return code_files


def send_message(chat, message, print_response=True):
    """Sends a message to the Gemini chat session with specified settings"""
    full_response = ""
    for response in chat._send_message_streaming(message, generation_config=GENERATION_CONFIG, safety_settings=SAFETY_SETTINGS):
        full_response += response.text
        if print_response:
            print(response.text, end="")
    if print_response:
        print("\n\n---------------\n\n")
    return full_response


def analyze_codebase(chat, files):
    """Analyzes the provided code files using a multi-turn conversation with Gemini."""

    initial_prompt = """
    Here is a code repository. Just respond "OK".
    Code files :
    """ + "".join([f"{filename} : \n{content}\n" for filename, content in files.items()])

    list_of_paths = "\n".join(files.keys())

    list_of_paths_prompt = f"""
        Here is the list of files in the project :
        {list_of_paths}
        Just respond with "OK".
    """
    
    send_message(chat, initial_prompt)
    send_message(chat, list_of_paths_prompt)
    generated_readme = send_message(chat, """
        Now write a description in two part of approximately the same length. It is a internal description that will help other internal developers understand the project.
        Focus on objective points and description instead of subjective thoughts such as why the project is well-written.
        The first part focuses on the purpose of the project, and should be business oriented. Be specific and get into the details of the business logic.
        The second part focuses on how the project works internally.
        Write your answer in french.
    """)

    return generated_readme



app = FastAPI()

# WebSocket connection management
active_connections = set()
active_chats = {}  # Track active chats for each client


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"Client connected")
    await websocket.accept()
    active_connections.add(websocket)
    active_chats[websocket] = None  # Initialize chat for this client
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Retrieve or create chat for this client
            chat = active_chats.get(websocket)
            if not chat:
                chat = GenerativeModel(MODEL_NAME).start_chat()
                active_chats[websocket] = chat

            if message.get("action") == "analyze":
                # Start analysis in a separate thread
                repo_url = message.get("repoUrl")
                if not repo_url:
                    await websocket.send_text(json.dumps({"error": "Missing 'repoUrl' in message"}))
                    continue

                await websocket.send_text(json.dumps({"message": "Analysis started..."}))
                # Clone the Git repository

                # await this block using asyncio
                def clone_and_analyze():
                    # Clone the Git repository
                    repo_dir = os.path.join("/tmp", os.path.basename(repo_url))
                    if os.path.exists(repo_dir):
                        os.system(f"rm -rf {repo_dir}")
                    git.Repo.clone_from(repo_url, repo_dir)

                    code_extensions = get_code_file_extensions(repo_dir)
                    code_files = read_code_files(repo_dir, code_extensions)
                    return analyze_codebase(chat, code_files)

                generated_readme = await asyncio.create_task(asyncio.to_thread(clone_and_analyze))
                await websocket.send_text(json.dumps({"readme": generated_readme}))

            elif message.get("action") == "prompt":
                # Send user prompt to the existing chat
                user_message = message.get("message")
                if not user_message:
                    await websocket.send_text(json.dumps({"error": "Missing 'message' in prompt"}))
                    continue

                try:
                    def get_response():
                        return send_message(chat, user_message + "\n\nRenvoie le README complet avec les modifications.", print_response=False)

                    response = await asyncio.create_task(asyncio.to_thread(get_response))
                    await websocket.send_text(json.dumps({"response": response}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"error": str(e)}))

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        active_chats.pop(websocket, None)  # Remove chat for this client
    except Exception as e:
        print(f"WebSocket error: {e}")

import asyncio

import uvicorn

if __name__ == "__main__":
    # ... (Your code to set PROJECT_ID and LOCATION remains the same) ...
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)