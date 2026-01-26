# API Documentation

## Overview

This Django application provides a complete CRUD API for managing Users, Projects, and Tags with authentication support.

## Base URL

```
http://localhost:8000
```

## Running the Server

To make the server accessible from external sources:

```bash
python3 manage.py runserver 0.0.0.0:8000
```

**Note:** `ALLOWED_HOSTS` is already configured to accept all hosts for development.

---

## Authentication

### Login Page

**URL:** `/login/`  
**Method:** `GET`  
**Description:** Renders the login/register page

### Register User

**URL:** `/api/auth/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "action": "register",
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": "60d5ec49f1b2c8b9e8c4a123",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

**Error Response (400):**
```json
{
  "status": "error",
  "message": "Email already registered"
}
```

### Login

**URL:** `/api/auth/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "action": "login",
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Login successful",
  "user": {
    "id": "60d5ec49f1b2c8b9e8c4a123",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

**Error Response (401):**
```json
{
  "status": "error",
  "message": "Invalid credentials"
}
```

### Logout

**URL:** `/api/auth/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "action": "logout"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Logout successful"
}
```

---

## User Management

### List All Users

**URL:** `/api/users/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "users": [
    {
      "id": "60d5ec49f1b2c8b9e8c4a123",
      "name": "John Doe",
      "email": "john@example.com",
      "project_ids": [],
      "created_at": "2026-01-23T20:00:00Z",
      "is_active": true
    }
  ],
  "count": 1
}
```

### Get Single User

**URL:** `/api/users/<user_id>/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "user": {
    "id": "60d5ec49f1b2c8b9e8c4a123",
    "name": "John Doe",
    "email": "john@example.com",
    "project_ids": [],
    "created_at": "2026-01-23T20:00:00Z",
    "is_active": true
  }
}
```

**Error Response (404):**
```json
{
  "status": "error",
  "message": "User not found"
}
```

### Create User

**URL:** `/api/users/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "password": "securepassword",
  "project_ids": []
}
```

**Success Response (201):**
```json
{
  "status": "success",
  "message": "User created",
  "user": {
    "id": "60d5ec49f1b2c8b9e8c4a124",
    "name": "Jane Smith",
    "email": "jane@example.com"
  }
}
```

### Update User

**URL:** `/api/users/<user_id>/`  
**Method:** `PUT`  
**Content-Type:** `application/json`

**Request Body (all fields optional):**
```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "password": "newpassword",
  "project_ids": ["project_id_1", "project_id_2"],
  "is_active": true
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "User updated",
  "user": {
    "id": "60d5ec49f1b2c8b9e8c4a124",
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "is_active": true
  }
}
```

### Delete User

**URL:** `/api/users/<user_id>/`  
**Method:** `DELETE`

**Success Response (200):**
```json
{
  "status": "success",
  "message": "User deleted"
}
```

---

## Project Management

### List All Projects

**URL:** `/api/projects/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "projects": [
    {
      "id": "60d5ec49f1b2c8b9e8c4a125",
      "name": "My Project",
      "description": "Project description",
      "tags": {"category": "web"},
      "date_created": "2026-01-23T20:00:00Z",
      "date_updated": "2026-01-23T20:00:00Z"
    }
  ],
  "count": 1
}
```

### Get Single Project

**URL:** `/api/projects/<project_id>/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "project": {
    "id": "60d5ec49f1b2c8b9e8c4a125",
    "name": "My Project",
    "description": "Project description",
    "tags": {"category": "web"},
    "date_created": "2026-01-23T20:00:00Z",
    "date_updated": "2026-01-23T20:00:00Z"
  }
}
```

### Create Project

**URL:** `/api/projects/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "New Project",
  "description": "Project description",
  "tags": {"category": "mobile", "priority": "high"}
}
```

**Success Response (201):**
```json
{
  "status": "success",
  "message": "Project created",
  "project": {
    "id": "60d5ec49f1b2c8b9e8c4a126",
    "name": "New Project",
    "description": "Project description",
    "tags": {"category": "mobile", "priority": "high"}
  }
}
```

### Update Project

**URL:** `/api/projects/<project_id>/`  
**Method:** `PUT`  
**Content-Type:** `application/json`

**Request Body (all fields optional):**
```json
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "tags": {"category": "web", "status": "active"}
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Project updated",
  "project": {
    "id": "60d5ec49f1b2c8b9e8c4a126",
    "name": "Updated Project Name",
    "description": "Updated description",
    "tags": {"category": "web", "status": "active"}
  }
}
```

### Delete Project

**URL:** `/api/projects/<project_id>/`  
**Method:** `DELETE`

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Project deleted"
}
```

---

## Tag Management

### List All Tags

**URL:** `/api/tags/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "tags": [
    {
      "id": "60d5ec49f1b2c8b9e8c4a127",
      "numeric_id": 1,
      "name": "Important"
    }
  ],
  "count": 1
}
```

### Get Single Tag

**URL:** `/api/tags/<tag_id>/`  
**Method:** `GET`

**Success Response (200):**
```json
{
  "status": "success",
  "tag": {
    "id": "60d5ec49f1b2c8b9e8c4a127",
    "numeric_id": 1,
    "name": "Important"
  }
}
```

### Create Tag

**URL:** `/api/tags/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "numeric_id": 2,
  "name": "Urgent"
}
```

**Success Response (201):**
```json
{
  "status": "success",
  "message": "Tag created",
  "tag": {
    "id": "60d5ec49f1b2c8b9e8c4a128",
    "numeric_id": 2,
    "name": "Urgent"
  }
}
```

**Error Response (400):**
```json
{
  "status": "error",
  "message": "Tag with this numeric_id already exists"
}
```

### Update Tag

**URL:** `/api/tags/<tag_id>/`  
**Method:** `PUT`  
**Content-Type:** `application/json`

**Request Body (all fields optional):**
```json
{
  "numeric_id": 3,
  "name": "Critical"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Tag updated",
  "tag": {
    "id": "60d5ec49f1b2c8b9e8c4a128",
    "numeric_id": 3,
    "name": "Critical"
  }
}
```

### Delete Tag

**URL:** `/api/tags/<tag_id>/`  
**Method:** `DELETE`

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Tag deleted"
}
```

---

## S3 File Upload (Existing)

### Upload File to S3

**URL:** `/s3/`  
**Method:** `POST`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "bucket_name": "my-bucket",
  "key": "myfile.txt",
  "content": "File content here",
  "project_id": "60d5ec49f1b2c8b9e8c4a125",
  "tag_ids": ["60d5ec49f1b2c8b9e8c4a127"]
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "message": "File uploaded to S3",
  "image_id": "60d5ec49f1b2c8b9e8c4a129",
  "metadata": {
    "path": "s3://my-bucket/myfile.txt",
    "size": 17,
    "content_type": "text/plain",
    "etag": "abc123",
    "last_modified": "2026-01-23T20:00:00Z"
  }
}
```

---

## Testing the API

### Using curl

**Register a user:**
```bash
curl -X POST http://localhost:8000/api/auth/ \
  -H "Content-Type: application/json" \
  -d '{"action":"register","name":"Test User","email":"test@example.com","password":"password123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/ \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"action":"login","email":"test@example.com","password":"password123"}'
```

**Create a project:**
```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"My Project","description":"Test project","tags":{"type":"web"}}'
```

**List all projects:**
```bash
curl http://localhost:8000/api/projects/
```

### Using Python

```python
import requests

# Register
response = requests.post('http://localhost:8000/api/auth/', json={
    'action': 'register',
    'name': 'Test User',
    'email': 'test@example.com',
    'password': 'password123'
})
print(response.json())

# Login
session = requests.Session()
response = session.post('http://localhost:8000/api/auth/', json={
    'action': 'login',
    'email': 'test@example.com',
    'password': 'password123'
})
print(response.json())

# Create project
response = session.post('http://localhost:8000/api/projects/', json={
    'name': 'My Project',
    'description': 'Test project',
    'tags': {'type': 'web'}
})
print(response.json())
```

---

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "status": "error",
  "message": "Description of the error"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created successfully
- `400` - Bad request (missing or invalid parameters)
- `401` - Unauthorized (authentication required or invalid credentials)
- `404` - Not found
- `500` - Internal server error

---

## Database

The application uses MongoDB for data storage. Models include:

- **User**: name, email, password_hash, project_ids, created_at, is_active
- **Project**: name, description, tags, date_created, date_updated
- **Tag**: numeric_id, name
- **Image**: S3 file metadata

Connection: `mongodb://admin:password@localhost:27017/`
