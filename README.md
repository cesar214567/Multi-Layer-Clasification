# Django MVC with S3 and MongoDB

Django application with complete CRUD API for User, Project, and Tag management, authentication system, and S3/MongoDB integration.

## Features

✅ **Authentication System**
- User registration and login with password hashing
- Session-based authentication
- Beautiful login/register page with modern UI

✅ **Complete CRUD Operations**
- Users: Create, Read, Update, Delete with password management
- Projects: Full CRUD with tags and descriptions
- Tags: Full CRUD with numeric IDs

✅ **External Access**
- Server configured to accept connections from external sources
- ALLOWED_HOSTS properly configured

✅ **Security**
- Password hashing using Django's built-in hashers
- Email uniqueness validation
- Active user status management

## Setup

1. **Python 3.10+ required** (for ultralytics/YOLO support)

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start services:**
```bash
docker-compose up -d
```

3. **Run Django server (accessible externally):**
```bash
python3.10 manage.py runserver 0.0.0.0:8000
```

**Important:** Use `0.0.0.0:8000` to make the server accessible from external sources, not just `localhost:8000`.

## Quick Start

1. Visit the login page: `http://localhost:8000/login/`
2. Register a new account
3. Use the API endpoints to manage users, projects, and tags

## API Endpoints

### Authentication
- `GET /login/` - Login/Register page
- `POST /api/auth/` - Login, Register, Logout

### Users (Full CRUD)
- `GET /api/users/` - List all users
- `GET /api/users/<id>/` - Get single user
- `POST /api/users/` - Create user
- `PUT /api/users/<id>/` - Update user
- `DELETE /api/users/<id>/` - Delete user

### Projects (Full CRUD)
- `GET /api/projects/` - List all projects
- `GET /api/projects/<id>/` - Get single project
- `POST /api/projects/` - Create project
- `PUT /api/projects/<id>/` - Update project
- `DELETE /api/projects/<id>/` - Delete project

### Tags (Full CRUD)
- `GET /api/tags/` - List all tags
- `GET /api/tags/<id>/` - Get single tag
- `POST /api/tags/` - Create tag
- `PUT /api/tags/<id>/` - Update tag
- `DELETE /api/tags/<id>/` - Delete tag

### Trained Models (Full CRUD)
- `GET /api/trained-models/` - List all trained models
- `GET /api/trained-models/<id>/` - Get single trained model (includes version history)
- `POST /api/trained-models/` - Create trained model (requires `project_id`)
- `PUT /api/trained-models/<id>/` - Update trained model (creates a new version)
- `DELETE /api/trained-models/<id>/` - Delete trained model

### Training
- `POST /api/trained-models/train/` - Train a model using project images

### Trained Model Inference
- `POST /api/trained-models/inference/` - Run inference with a trained model (multipart/form-data: `trained_model_id`, `image`, optional `version`)

### PreTrained Models (Full CRUD)
- `GET /api/pretrained-models/` - List all pretrained models
- `GET /api/pretrained-models/<id>/` - Get single pretrained model
- `POST /api/pretrained-models/` - Build new pretrained model or attach existing to project
- `PUT /api/pretrained-models/<id>/` - Update pretrained model
- `DELETE /api/pretrained-models/<id>/` - Delete pretrained model

### PreTrained Model Inference
- `POST /api/inference/` - Run inference with a pretrained model (multipart/form-data: `project_id`, `pretrained_model_id`, `image`)

### PreTrained Detection Models (YOLO) (Full CRUD)
- `GET /api/pretrained-detection-models/` - List all pretrained detection models
- `GET /api/pretrained-detection-models/<id>/` - Get single pretrained detection model
- `POST /api/pretrained-detection-models/` - Download YOLO model and upload to S3, or attach existing to project
- `PUT /api/pretrained-detection-models/<id>/` - Update pretrained detection model
- `DELETE /api/pretrained-detection-models/<id>/` - Delete pretrained detection model

### PreTrained Detection Model Inference
- `POST /api/pretrained-detection-models/inference/` - Run inference with a YOLO model (multipart/form-data: `pretrained_detection_model_id`, `image`, optional `confidence`). Returns a ZIP file containing `results.json`, annotated image, and mask PNGs (segmentation only). Task is auto-detected from the model.

### Images (Full CRUD)
- `GET /api/images/` - List all images
- `GET /api/images/<id>/` - Get single image
- `POST /api/images/` - Upload image to S3 (multipart/form-data: `user_id`, `project_id`, `file`, optional `tags`)
- `PUT /api/images/<id>/` - Update image metadata
- `DELETE /api/images/<id>/` - Delete image

### S3 Storage
- `POST /s3/` - Upload file to S3

## Documentation

- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference with examples
- **[postman_collection.json](postman_collection.json)** - Import this file into Postman to test all API endpoints
- **[insomnia_collection.json](insomnia_collection.json)** - Import this file into Insomnia (alternative to Postman)

### Using Postman (Recommended)

1. Open Postman
2. Click **"Import"** button (top left)
3. Select `postman_collection.json`
4. The collection will be imported with all endpoints organized in folders:
   - Authentication (Register, Login, Logout)
   - Users CRUD (List, Get, Create, Update, Delete)
   - Projects CRUD (List, Get, Create, Update, Delete)
   - Tags CRUD (List, Get, Create, Update, Delete)
   - S3 Storage
   - Miscellaneous
5. Collection variables are pre-configured:
   - `base_url`: http://localhost:8000
   - `user_id`: (fill after creating a user)
   - `project_id`: (fill after creating a project)
   - `tag_id`: (fill after creating a tag)

### Using Insomnia (Alternative)

1. Open Insomnia
2. Click **"Import/Export"** → **"Import Data"** → **"From File"**
3. Select `insomnia_collection.json`
4. All endpoints will be organized in folders
5. Update environment variables if needed

## Example Usage

### Register a User
```bash
curl -X POST http://localhost:8000/api/auth/ \
  -H "Content-Type: application/json" \
  -d '{"action":"register","name":"John Doe","email":"john@example.com","password":"password123"}'
```

### Create a Project
```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name":"My Project","description":"A test project","tags":{"category":"web"}}'
```

### List All Users
```bash
curl http://localhost:8000/api/users/
```

## Services

### Docker Services
The project uses Docker Compose to run the following services:

#### MongoDB Database
- **Container**: mongodb
- **Port**: 27017
- **Root Username**: admin
- **Root Password**: password
- **Image**: mongo:latest

#### LocalStack S3
- **Container**: localstack-s3
- **Port**: 4566
- **Services**: S3
- **Image**: localstack/localstack:latest

#### Django Application
- **Port**: 8000 (accessible from external sources on 0.0.0.0:8000)

### Starting the Services
```bash
# Start all services in detached mode
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart a specific service
docker-compose restart mongodb
```

## Database Configuration

### MongoDB Connection Strings

#### Local Connection (from the same machine)
```
mongodb://admin:password@localhost:27017/?authSource=admin
```

#### Remote Connection (from another PC)
Replace `YOUR_HOSTNAME` with your actual hostname :

```
mongodb://admin:password@YOUR_HOSTNAME:27017/?authSource=admin
```

**For connecting to a specific database:**
```
mongodb://admin:password@YOUR_HOSTNAME:27017/your_database_name?authSource=admin
```

#### Connection Details
- **Username**: `admin`
- **Password**: `password`
- **Host**: `localhost` (local) or your server hostname (remote)
- **Port**: `27017`
- **Auth Source**: `admin` (required for root user authentication)

#### Important Notes for Remote Connections
1. **Port Access**: Ensure port 27017 is open in your firewall/security group settings
2. **Auth Source**: The `authSource=admin` parameter is required when using root credentials
3. **Network**: Make sure the MongoDB container is accessible from external networks if needed
4. **Security**: Consider using more secure credentials in production environments

### MongoDB GUI Clients
You can connect to the MongoDB database using any MongoDB client:
- **MongoDB Compass**: Official MongoDB GUI (recommended)
- **Studio 3T**: Advanced MongoDB GUI
- **Robo 3T**: Lightweight MongoDB GUI

### LocalStack S3 Configuration

#### Endpoint
```
http://localhost:4566
```

#### AWS CLI Configuration
```bash
# Configure AWS CLI for LocalStack
aws configure --profile localstack
# AWS Access Key ID: test
# AWS Secret Access Key: test
# Default region name: us-east-1
# Default output format: json

# Use LocalStack endpoint
aws --endpoint-url=http://localhost:4566 s3 ls --profile localstack
```

#### Python boto3 Configuration
```python
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)
```

## Models

- **User**: name, email, password_hash, project_ids, projects, created_at, is_active
- **Project**: name, description, tags, trained_models, pretrained_models, pretrained_detection_models, user, date_created, date_updated
- **Tag**: name, project
- **TrainedModel**: name, description, project, architecture, include_top, custom_top_layers, custom_architecture, tags, epochs, batch_size, img_size, learning_rate, loss, metrics, current_version, versions, date_created, date_updated
- **PreTrainedModel**: name, description, path, format, size, enabled, date_created, date_updated
- **PreTrainedDetectionModel**: name, description, path, format, size, architecture, task, dataset, enabled, date_created, date_updated
- **Image**: path, bucket_name, key, size, format, content_type, etag, last_modified, project, tag_references

## Troubleshooting

### Server not accessible externally?
Make sure you're running the server with:
```bash
python3 manage.py runserver 0.0.0.0:8000
```
Not just `python3 manage.py runserver` (which only binds to localhost).

## PreTrained Model Architectures

When calling `POST /api/pretrained-models/`, the `architecture` field accepts any of the following values (case-insensitive, hyphens and underscores are ignored):

| Architecture | Value to send |
|---|---|
| ConvNeXt Base | `ConvNeXtBase` |
| ConvNeXt Large | `ConvNeXtLarge` |
| ConvNeXt Small | `ConvNeXtSmall` |
| ConvNeXt Tiny | `ConvNeXtTiny` |
| ConvNeXt XLarge | `ConvNeXtXLarge` |
| DenseNet-121 | `DenseNet121` |
| DenseNet-169 | `DenseNet169` |
| DenseNet-201 | `DenseNet201` |
| EfficientNet B0 | `EfficientNetB0` |
| EfficientNet B1 | `EfficientNetB1` |
| EfficientNet B2 | `EfficientNetB2` |
| EfficientNet B3 | `EfficientNetB3` |
| EfficientNet B4 | `EfficientNetB4` |
| EfficientNet B5 | `EfficientNetB5` |
| EfficientNet B6 | `EfficientNetB6` |
| EfficientNet B7 | `EfficientNetB7` |
| EfficientNetV2 B0 | `EfficientNetV2B0` |
| EfficientNetV2 B1 | `EfficientNetV2B1` |
| EfficientNetV2 B2 | `EfficientNetV2B2` |
| EfficientNetV2 B3 | `EfficientNetV2B3` |
| EfficientNetV2 L | `EfficientNetV2L` |
| EfficientNetV2 M | `EfficientNetV2M` |
| EfficientNetV2 S | `EfficientNetV2S` |
| Inception-ResNet V2 | `InceptionResNetV2` |
| Inception V3 | `InceptionV3` |
| MobileNet | `MobileNet` |
| MobileNet V2 | `MobileNetV2` |
| MobileNet V3 Large | `MobileNetV3Large` |
| MobileNet V3 Small | `MobileNetV3Small` |
| NASNet Large | `NASNetLarge` |
| NASNet Mobile | `NASNetMobile` |
| RegNetX 002 | `RegNetX002` |
| RegNetX 004 | `RegNetX004` |
| RegNetX 006 | `RegNetX006` |
| RegNetX 008 | `RegNetX008` |
| RegNetX 016 | `RegNetX016` |
| RegNetX 032 | `RegNetX032` |
| RegNetX 040 | `RegNetX040` |
| RegNetX 064 | `RegNetX064` |
| RegNetX 080 | `RegNetX080` |
| RegNetX 120 | `RegNetX120` |
| RegNetX 160 | `RegNetX160` |
| RegNetX 320 | `RegNetX320` |
| RegNetY 002 | `RegNetY002` |
| RegNetY 004 | `RegNetY004` |
| RegNetY 006 | `RegNetY006` |
| RegNetY 008 | `RegNetY008` |
| RegNetY 016 | `RegNetY016` |
| RegNetY 032 | `RegNetY032` |
| RegNetY 040 | `RegNetY040` |
| RegNetY 064 | `RegNetY064` |
| RegNetY 080 | `RegNetY080` |
| RegNetY 120 | `RegNetY120` |
| RegNetY 160 | `RegNetY160` |
| RegNetY 320 | `RegNetY320` |
| ResNet-101 | `ResNet101` |
| ResNet-101 V2 | `ResNet101V2` |
| ResNet-152 | `ResNet152` |
| ResNet-152 V2 | `ResNet152V2` |
| ResNet-50 | `ResNet50` |
| ResNet-50 V2 | `ResNet50V2` |
| ResNetRS-101 | `ResNetRS101` |
| ResNetRS-152 | `ResNetRS152` |
| ResNetRS-200 | `ResNetRS200` |
| ResNetRS-270 | `ResNetRS270` |
| ResNetRS-350 | `ResNetRS350` |
| ResNetRS-420 | `ResNetRS420` |
| ResNetRS-50 | `ResNetRS50` |
| VGG-16 | `VGG16` |
| VGG-19 | `VGG19` |
| Xception | `Xception` |

### Example request — build a new model

```bash
curl -X POST http://localhost:8000/api/pretrained-models/ \
  -H "Content-Type: application/json" \
  -d '{
    "architecture": "VGG19",
    "dataset": "imagenet",
    "project_id": "<optional-project-id>"
  }'
```

### Example request — attach an existing model to a project

Use `attach_existing: true` to link an already-created `PreTrainedModel` to a project **without** re-building or re-uploading anything.

The model can be identified in two ways (checked in this order):

**Option 1 — by MongoDB ID:**
```bash
curl -X POST http://localhost:8000/api/pretrained-models/ \
  -H "Content-Type: application/json" \
  -d '{
    "attach_existing": true,
    "pretrained_model_id": "<pretrained-model-id>",
    "project_id": "<project-id>"
  }'
```

**Option 2 — by compound name (`{Architecture}_{dataset}`, e.g. `VGG19_imagenet`):**
```bash
curl -X POST http://localhost:8000/api/pretrained-models/ \
  -H "Content-Type: application/json" \
  -d '{
    "attach_existing": true,
    "architecture": "VGG19",
    "dataset": "imagenet",
    "project_id": "<project-id>"
  }'
```
> `dataset` defaults to `"imagenet"` when omitted.

| Field | Required | Description |
|---|---|---|
| `attach_existing` | ✅ | Set to `true` to activate attach mode |
| `project_id` | ✅ | MongoDB ObjectId of the target `Project` |
| `pretrained_model_id` | ⚡ priority 1 | MongoDB ObjectId of the existing `PreTrainedModel` |
| `architecture` | ⚡ priority 2 | Architecture name — used together with `dataset` to build the compound name `{Architecture}_{dataset}` |
| `dataset` | optional | Dataset name (default: `imagenet`) — used with `architecture` for compound-name lookup |

**Validations performed:**
- Returns `400` if neither `pretrained_model_id` nor `architecture` is provided.
- Returns `400` if `architecture` is not a recognised Keras architecture.
- Returns `404` if no model matches the provided id or compound name.
- Returns `404` if `project_id` does not match any stored project.
- Returns `400` if the model is already attached to that project (duplicate prevention).

### Notes
- The `dataset` field defaults to `"imagenet"`. Only `"imagenet"` weights are officially supported by Keras; any other value will initialize the model with random weights.
- Architecture names are matched **case-insensitively** with hyphens and underscores ignored, so `"vgg19"`, `"VGG19"`, and `"VGG-19"` all work.
- When `attach_existing` is `true`, TensorFlow is **not** loaded — the request is fast and lightweight.

## PreTrained Detection Models (YOLO)

When calling `POST /api/pretrained-detection-models/`, the `model` field accepts any of the following YOLO model names (case-insensitive, `.pt` extension optional):

### Detection — COCO

| Family | Models |
|---|---|
| YOLOv3 | `yolov3u`, `yolov3-sppu`, `yolov3-tinyu` |
| YOLOv5 | `yolov5nu`, `yolov5su`, `yolov5mu`, `yolov5lu`, `yolov5xu` |
| YOLOv5-P6 | `yolov5n6u`, `yolov5s6u`, `yolov5m6u`, `yolov5l6u`, `yolov5x6u` |
| YOLOv8 | `yolov8n`, `yolov8s`, `yolov8m`, `yolov8l`, `yolov8x` |
| YOLOv9 | `yolov9t`, `yolov9s`, `yolov9m`, `yolov9c`, `yolov9e` |
| YOLOv10 | `yolov10n`, `yolov10s`, `yolov10m`, `yolov10b`, `yolov10l`, `yolov10x` |
| YOLO11 | `yolo11n`, `yolo11s`, `yolo11m`, `yolo11l`, `yolo11x` |
| YOLO12 | `yolo12n`, `yolo12s`, `yolo12m`, `yolo12l`, `yolo12x` |
| YOLO26 | `yolo26n`, `yolo26s`, `yolo26m`, `yolo26l`, `yolo26x` |
| RT-DETR | `rtdetr-l`, `rtdetr-x` |

### Detection — Open Images V7

| Models |
|---|
| `yolov8n-oiv7`, `yolov8s-oiv7`, `yolov8m-oiv7`, `yolov8l-oiv7`, `yolov8x-oiv7` |

### Detection — Open Vocabulary (World)

| Family | Models |
|---|---|
| World v1 | `yolov8s-world`, `yolov8m-world`, `yolov8l-world`, `yolov8x-world` |
| World v2 | `yolov8s-worldv2`, `yolov8m-worldv2`, `yolov8l-worldv2`, `yolov8x-worldv2` |

### Segmentation — COCO

| Family | Models |
|---|---|
| YOLOv8 | `yolov8n-seg`, `yolov8s-seg`, `yolov8m-seg`, `yolov8l-seg`, `yolov8x-seg` |
| YOLOv9 | `yolov9c-seg`, `yolov9e-seg` |
| YOLO11 | `yolo11n-seg`, `yolo11s-seg`, `yolo11m-seg`, `yolo11l-seg`, `yolo11x-seg` |
| YOLO26 | `yolo26n-seg`, `yolo26s-seg`, `yolo26m-seg`, `yolo26l-seg`, `yolo26x-seg` |

### Classification — ImageNet

| Family | Models |
|---|---|
| YOLOv8 | `yolov8n-cls`, `yolov8s-cls`, `yolov8m-cls`, `yolov8l-cls`, `yolov8x-cls` |
| YOLO11 | `yolo11n-cls`, `yolo11s-cls`, `yolo11m-cls`, `yolo11l-cls`, `yolo11x-cls` |
| YOLO26 | `yolo26n-cls`, `yolo26s-cls`, `yolo26m-cls`, `yolo26l-cls`, `yolo26x-cls` |

### Pose Estimation — COCO

| Family | Models |
|---|---|
| YOLOv8 | `yolov8n-pose`, `yolov8s-pose`, `yolov8m-pose`, `yolov8l-pose`, `yolov8x-pose` |
| YOLO11 | `yolo11n-pose`, `yolo11s-pose`, `yolo11m-pose`, `yolo11l-pose`, `yolo11x-pose` |
| YOLO26 | `yolo26n-pose`, `yolo26s-pose`, `yolo26m-pose`, `yolo26l-pose`, `yolo26x-pose` |

### Oriented Bounding Boxes (OBB) — DOTAv1

| Family | Models |
|---|---|
| YOLOv8 | `yolov8n-obb`, `yolov8s-obb`, `yolov8m-obb`, `yolov8l-obb`, `yolov8x-obb` |
| YOLO11 | `yolo11n-obb`, `yolo11s-obb`, `yolo11m-obb`, `yolo11l-obb`, `yolo11x-obb` |
| YOLO26 | `yolo26n-obb`, `yolo26s-obb`, `yolo26m-obb`, `yolo26l-obb`, `yolo26x-obb` |

### Segment Anything (SAM)

| Family | Models |
|---|---|
| SAM | `sam_b`, `sam_l` |
| SAM 2 | `sam2_t`, `sam2_s`, `sam2_b`, `sam2_l` |
| SAM 2.1 | `sam2.1_t`, `sam2.1_s`, `sam2.1_b`, `sam2.1_l` |
| FastSAM | `FastSAM-s`, `FastSAM-x`, `mobile_sam` |

### YOLO-NAS

| Models |
|---|
| `yolo_nas_s`, `yolo_nas_m`, `yolo_nas_l` |

### Example request — download and upload a YOLO model

```bash
curl -X POST http://localhost:8000/api/pretrained-detection-models/ \
  -H "Content-Type: application/json" \
  -d '{
    "model": "yolov8n",
    "dataset": "coco",
    "project_id": "<optional-project-id>",
    "description": "YOLOv8 Nano detection model"
  }'
```

### Example request — attach an existing YOLO model to a project

```bash
curl -X POST http://localhost:8000/api/pretrained-detection-models/ \
  -H "Content-Type: application/json" \
  -d '{
    "model": "yolov8n",
    "dataset": "coco",
    "attach_existing": true,
    "project_id": "<project-id>"
  }'
```

### Notes
- Model names are matched **case-insensitively**; the `.pt` extension is optional.
- The `dataset` field is **optional**. If omitted, the default dataset for the model is used (e.g. `coco` for detection models, `imagenet` for `-cls` models). If provided, the model+dataset combination is validated and returns `400` if invalid.
- The task (detect, segment, classify, pose, obb) is inferred automatically from the model name suffix.
- If the model has already been downloaded and uploaded to S3, a subsequent POST will skip the download and just attach it to the project (if `project_id` is provided).
- When `attach_existing` is `true`, Ultralytics is **not** loaded — the request is fast and lightweight.
