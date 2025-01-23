import os
import json
import requests
from dotenv import load_dotenv

OPENWEBUI_URL = "https://llm.oculair.ca"

def get_jwt_token():
    load_dotenv()
    token = os.getenv("OPENWEBUI_JWT_TOKEN")
    if not token:
        raise ValueError("OPENWEBUI_JWT_TOKEN not found in .env file")
    return token

def upload_function(name, content, description=""):
    """Upload a function to OpenWebUI"""
    
    OPENWEBUI_JWT_TOKEN = get_jwt_token()
    
    url = f"{OPENWEBUI_URL}/api/v1/functions/create"
    headers = {
        "Authorization": f"Bearer {OPENWEBUI_JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "OpenWebUI-Function-Uploader/1.0"
    }
    
    payload = {
        "id": f"custom_{name.lower().replace(' ', '_')}",
        "name": name,
        "content": content,
        "meta": {
            "description": description,
            "manifest": {}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error uploading function: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

if __name__ == "__main__":
    # Example usage
    function_name = input("Enter function name: ")
    function_content = input("Enter function content: ")
    function_description = input("Enter function description (optional): ")
    
    result = upload_function(function_name, function_content, function_description)
    
    if result:
        print("Function uploaded successfully!")
        print("Function ID:", result.get("id"))
    else:
        print("Failed to upload function")