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

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start services:**
```bash
docker-compose up -d
```

3. **Run Django server (accessible externally):**
```bash
python3 manage.py runserver 0.0.0.0:8000
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
Replace `YOUR_HOSTNAME` with your actual hostname (e.g., `dev-dsk-cesarmg-1d-ddce7a67.us-east-1.amazon.com`):

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

- **User**: name, email, password_hash, project_ids, created_at, is_active
- **Project**: name, description, tags, date_created, date_updated
- **Tag**: numeric_id, name
- **Image**: S3 file metadata with project and tag references

## Troubleshooting

### Server not accessible externally?
Make sure you're running the server with:
```bash
python3 manage.py runserver 0.0.0.0:8000
```
Not just `python3 manage.py runserver` (which only binds to localhost).
