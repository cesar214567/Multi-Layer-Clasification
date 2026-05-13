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

## Trained Model Management

### List All Trained Models

**URL:** `/api/trained-models/`
**Method:** `GET`

### Get Single Trained Model

**URL:** `/api/trained-models/<model_id>/`
**Method:** `GET`

**Response includes version history.**

### Create Trained Model

**URL:** `/api/trained-models/`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "My Classifier",
  "description": "Image classifier",
  "project_id": "<project-id>",
  "architecture": "MobileNetV2",
  "include_top": false,
  "custom_top_layers": [
    {"type": "GlobalAveragePooling2D"},
    {"type": "Dense", "units": 256, "activation": "relu"},
    {"type": "Dense", "units": 5, "activation": "softmax"}
  ],
  "tag_ids": ["<tag-id-1>", "<tag-id-2>"],
  "epochs": 10,
  "batch_size": 32,
  "img_size": 224,
  "learning_rate": 0.001,
  "loss": "sparse_categorical_crossentropy",
  "metrics": ["accuracy"]
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | ✅ | | Model name |
| `project_id` | ✅ | | Project to attach the model to |
| `architecture` | optional | | Keras architecture name or `"custom"` |
| `include_top` | optional | `true` | Whether to include the classification head |
| `custom_top_layers` | optional | `[]` | Replacement top layers when `include_top=false` |
| `custom_architecture` | optional | `[]` | Full layer list when `architecture="custom"` |
| `tag_ids` | optional | `[]` | Tag IDs for classification labels |
| `epochs` | optional | `10` | Training epochs |
| `batch_size` | optional | `32` | Training batch size |
| `img_size` | optional | `224` | Input image size |
| `learning_rate` | optional | `0.001` | Learning rate |
| `loss` | optional | `sparse_categorical_crossentropy` | Loss function |
| `metrics` | optional | `["accuracy"]` | Training metrics |

**Note:** When `tag_ids` are provided, the last `Dense` layer in `custom_top_layers` or `custom_architecture` is automatically adjusted to match the number of tags if mismatched.

### Update Trained Model

**URL:** `/api/trained-models/<model_id>/`
**Method:** `PUT`
**Content-Type:** `application/json`

Each update creates a new version. All fields are optional.

### Delete Trained Model

**URL:** `/api/trained-models/<model_id>/`
**Method:** `DELETE`

---

## Training

### Train a Model

**URL:** `/api/trained-models/train/`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "trained_model_id": "<trained-model-id>",
  "project_id": "<project-id>",
  "version_notes": "First training run"
}
```

Builds the model from the TrainedModel's architecture config, loads training images from S3 (project images labeled by tags), trains the model, uploads weights to S3, and creates a new version. Uses `loss` and `metrics` from the TrainedModel.

---

## Trained Model Inference

### Run Inference

**URL:** `/api/trained-models/inference/`
**Method:** `POST`
**Content-Type:** `multipart/form-data`

| Field | Required | Description |
|---|---|---|
| `trained_model_id` | ✅ | ID of the TrainedModel |
| `image` | ✅ | Image file to classify |
| `version` | optional | Version number (defaults to latest) |

**Example:**
```bash
curl -X POST http://localhost:8000/api/trained-models/inference/ \
  -F "trained_model_id=<id>" \
  -F "image=@/path/to/image.jpg" \
  -F "version=1"
```

**Success Response:**
```json
{
  "status": "success",
  "model_name": "My Classifier",
  "version": 1,
  "input_size": "224x224",
  "predictions": [
    {"label": "Orange Tabby Cat", "confidence": 87.32},
    {"label": "Havana Brown", "confidence": 12.68}
  ]
}
```

---

## PreTrained Model Management

### List All PreTrained Models

**URL:** `/api/pretrained-models/`
**Method:** `GET`

### Get Single PreTrained Model

**URL:** `/api/pretrained-models/<model_id>/`
**Method:** `GET`

### Create PreTrained Model

**URL:** `/api/pretrained-models/`
**Method:** `POST`
**Content-Type:** `application/json`

Builds a Keras model and uploads weights to S3, or attaches an existing model to a project. See README for full architecture list and attach mode details.

### Update PreTrained Model

**URL:** `/api/pretrained-models/<model_id>/`
**Method:** `PUT`

### Delete PreTrained Model

**URL:** `/api/pretrained-models/<model_id>/`
**Method:** `DELETE`

---

## PreTrained Model Inference

### Run Inference

**URL:** `/api/inference/`
**Method:** `POST`
**Content-Type:** `multipart/form-data`

| Field | Required | Description |
|---|---|---|
| `project_id` | ✅ | Project the model is attached to |
| `pretrained_model_id` | ✅ | ID of the PreTrainedModel |
| `image` | ✅ | Image file to classify |

**Success Response:**
```json
{
  "status": "success",
  "model_name": "VGG19_imagenet",
  "input_size": "224x224",
  "predictions": [
    {"class_id": "n02123045", "label": "tabby", "confidence": 45.23}
  ]
}
```

---

## PreTrained Detection Model Management (YOLO)

### List All PreTrained Detection Models

**URL:** `/api/pretrained-detection-models/`
**Method:** `GET`

### Get Single PreTrained Detection Model

**URL:** `/api/pretrained-detection-models/<model_id>/`
**Method:** `GET`

### Create PreTrained Detection Model

**URL:** `/api/pretrained-detection-models/`
**Method:** `POST`
**Content-Type:** `application/json`

Downloads a YOLO model from Ultralytics, uploads to S3, and optionally attaches to a project. If the model already exists in S3, it reuses it.

**Request Body:**
```json
{
  "model": "yolov8n",
  "project_id": "<optional-project-id>",
  "description": "<optional>"
}
```

| Field | Required | Description |
|---|---|---|
| `model` | ✅ | YOLO model name (e.g. `yolov8n`, `yolo11l-seg`, `yolov8l-oiv7`) |
| `project_id` | optional | Project to attach the model to |
| `attach_existing` | optional | Set `true` to attach an already-stored model without re-downloading |
| `description` | optional | Custom description |

**Supported tasks and datasets:**

| Task | Suffix | Dataset | Example |
|---|---|---|---|
| Detection | *(none)* | COCO | `yolov8n`, `yolo11l`, `yolo26x` |
| Detection | `-oiv7` | Open Images V7 | `yolov8l-oiv7` |
| Detection | `-world` / `-worldv2` | Open Vocabulary | `yolov8s-world` |
| Segmentation | `-seg` | COCO | `yolov8n-seg`, `yolo11m-seg` |
| Classification | `-cls` | ImageNet | `yolov8n-cls`, `yolo26l-cls` |
| Pose | `-pose` | COCO | `yolov8n-pose`, `yolo11s-pose` |
| OBB | `-obb` | DOTAv1 | `yolov8n-obb`, `yolo26m-obb` |

**Supported architectures:** YOLOv3, YOLOv5, YOLOv8, YOLOv9, YOLOv10, YOLO11, YOLO12, YOLO26, RT-DETR, YOLO-NAS, SAM, FastSAM. Each with size variants (n/s/m/l/x/b).

### Update PreTrained Detection Model

**URL:** `/api/pretrained-detection-models/<model_id>/`
**Method:** `PUT`

### Delete PreTrained Detection Model

**URL:** `/api/pretrained-detection-models/<model_id>/`
**Method:** `DELETE`

---

## Image Management

### List All Images

**URL:** `/api/images/`
**Method:** `GET`

### Get Single Image

**URL:** `/api/images/<image_id>/`
**Method:** `GET`

### Upload Image

**URL:** `/api/images/`
**Method:** `POST`
**Content-Type:** `multipart/form-data`

| Field | Required | Description |
|---|---|---|
| `user_id` | ✅ | User uploading the image |
| `project_id` | ✅ | Project this image belongs to |
| `file` | ✅ | Image file |
| `tags` | optional | JSON array of tag references |

### Update Image

**URL:** `/api/images/<image_id>/`
**Method:** `PUT`
**Content-Type:** `application/json`

### Delete Image

**URL:** `/api/images/<image_id>/`
**Method:** `DELETE`

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

- **User**: name, email, password_hash, project_ids, projects, created_at, is_active
- **Project**: name, description, tags, trained_models, pretrained_models, pretrained_detection_models, user, date_created, date_updated
- **Tag**: name, project
- **TrainedModel**: name, description, project, architecture, include_top, custom_top_layers, custom_architecture, tags, epochs, batch_size, img_size, learning_rate, loss, metrics, current_version, versions, date_created, date_updated
- **PreTrainedModel**: name, description, path, format, size, enabled, date_created, date_updated
- **PreTrainedDetectionModel**: name, description, path, format, size, architecture, task, dataset, enabled, date_created, date_updated
- **Image**: path, bucket_name, key, size, format, content_type, etag, last_modified, project, tag_references

Connection: `mongodb://admin:password@localhost:27017/`
