#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://localhost:8000"

def test_home():
    response = requests.get(f"{BASE_URL}/")
    print("Home:", response.json())

def test_mongo():
    # Test tag creation
    tag_data = {
        "tag": {"numeric_id": 1, "name": "landscape"}
    }
    response = requests.post(f"{BASE_URL}/mongo/", json=tag_data)
    tag_result = response.json()
    print("MongoDB Tag:", tag_result)
    
    tag_data2 = {
        "tag": {"numeric_id": 2, "name": "portrait"}
    }
    response = requests.post(f"{BASE_URL}/mongo/", json=tag_data2)
    tag_result2 = response.json()
    print("MongoDB Tag 2:", tag_result2)
    
    # Test project creation
    project_data = {
        "project": {
            "name": "My Project", 
            "description": "A test project",
            "tags": {"category": "web", "priority": "high"}
        }
    }
    response = requests.post(f"{BASE_URL}/mongo/", json=project_data)
    project_result = response.json()
    print("MongoDB Project:", project_result)
    
    # Test user creation with project ID
    user_data = {
        "user": {
            "name": "John Doe", 
            "email": "john@example.com",
            "project_ids": [project_result.get('id')] if project_result.get('id') else []
        }
    }
    response = requests.post(f"{BASE_URL}/mongo/", json=user_data)
    print("MongoDB User:", response.json())

def test_s3():
    data = {
        "bucket_name": "test-bucket",
        "key": "test-image.jpg",
        "content": "fake image content",
        "tag_ids": []  # Add tag IDs here when available
    }
    response = requests.post(f"{BASE_URL}/s3/", json=data)
    print("S3 Upload:", response.json())

if __name__ == "__main__":
    print("Testing Django MVC with S3 and MongoDB...")
    test_home()
    test_mongo()
    test_s3()
