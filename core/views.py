from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .services import S3Service
from .models import User, Project, Image, Tag, TagReference
import json
from bson import ObjectId
from functools import wraps

# Simple authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(self, request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        try:
            user = User.objects(id=user_id).first()
            if not user or not user.is_active:
                return JsonResponse({'status': 'error', 'message': 'Invalid user'}, status=401)
            request.user = user
        except:
            return JsonResponse({'status': 'error', 'message': 'Invalid session'}, status=401)
        return f(self, request, *args, **kwargs)
    return decorated_function

class HomeView(View):
    def get(self, request):
        return JsonResponse({'message': 'Django MVC with S3 and MongoDB'})

class LoginPageView(View):
    def get(self, request):
        return render(request, 'login.html')

@method_decorator(csrf_exempt, name='dispatch')
class AuthView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'register':
                # Register new user
                email = data.get('email')
                password = data.get('password')
                name = data.get('name')
                
                if not email or not password or not name:
                    return JsonResponse({'status': 'error', 'message': 'Email, password, and name are required'}, status=400)
                
                # Check if user exists
                if User.objects(email=email).first():
                    return JsonResponse({'status': 'error', 'message': 'Email already registered'}, status=400)
                
                # Create user with hashed password
                user = User(
                    email=email,
                    name=name,
                    password_hash=make_password(password)
                )
                user.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'User registered successfully',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'name': user.name
                    }
                })
            
            elif action == 'login':
                # Login user
                email = data.get('email')
                password = data.get('password')
                
                if not email or not password:
                    return JsonResponse({'status': 'error', 'message': 'Email and password are required'}, status=400)
                
                user = User.objects(email=email).first()
                if not user or not check_password(password, user.password_hash):
                    return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
                
                if not user.is_active:
                    return JsonResponse({'status': 'error', 'message': 'Account is disabled'}, status=401)
                
                # Set session
                request.session['user_id'] = str(user.id)
                request.session['user_email'] = user.email
                
                # Populate user's projects
                user_projects = Project.objects(user=user)
                projects_list = [{
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': project.tags,
                    'date_created': project.date_created.isoformat() if project.date_created else None,
                    'date_updated': project.date_updated.isoformat() if project.date_updated else None
                } for project in user_projects]
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Login successful',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'name': user.name,
                        'projects': projects_list
                    }
                })
            
            elif action == 'logout':
                request.session.flush()
                return JsonResponse({'status': 'success', 'message': 'Logout successful'})
            
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UserView(View):
    # GET - List all users or get specific user
    def get(self, request, user_id=None):
        try:
            if user_id:
                # Get specific user
                user = User.objects(id=user_id).first()
                if not user:
                    return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
                
                return JsonResponse({
                    'status': 'success',
                    'user': {
                        'id': str(user.id),
                        'name': user.name,
                        'email': user.email,
                        'project_ids': user.project_ids,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                        'is_active': user.is_active
                    }
                })
            else:
                # List all users
                users = User.objects.all()
                user_list = [{
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'project_ids': user.project_ids,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'is_active': user.is_active
                } for user in users]
                
                return JsonResponse({'status': 'success', 'users': user_list, 'count': len(user_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # POST - Create user
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')
            
            if not email or not password or not name:
                return JsonResponse({'status': 'error', 'message': 'Email, password, and name are required'}, status=400)
            
            # Check if user exists
            if User.objects(email=email).first():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
            
            user = User(
                email=email,
                name=name,
                password_hash=make_password(password),
                project_ids=data.get('project_ids', [])
            )
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'User created',
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email
                }
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # PUT - Update user
    def put(self, request, user_id):
        try:
            user = User.objects(id=user_id).first()
            if not user:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            
            data = json.loads(request.body)
            
            if 'name' in data:
                user.name = data['name']
            if 'email' in data:
                # Check if email is taken by another user
                existing = User.objects(email=data['email'], id__ne=user_id).first()
                if existing:
                    return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
                user.email = data['email']
            if 'password' in data:
                user.password_hash = make_password(data['password'])
            if 'project_ids' in data:
                user.project_ids = data['project_ids']
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'User updated',
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'is_active': user.is_active
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # DELETE - Delete user
    def delete(self, request, user_id):
        try:
            user = User.objects(id=user_id).first()
            if not user:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            
            user.delete()
            return JsonResponse({'status': 'success', 'message': 'User deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProjectView(View):
    # GET - List all projects or get specific project
    def get(self, request, project_id=None):
        try:
            if project_id:
                # Get specific project
                project = Project.objects(id=project_id).first()
                if not project:
                    return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
                
                return JsonResponse({
                    'status': 'success',
                    'project': {
                        'id': str(project.id),
                        'name': project.name,
                        'description': project.description,
                        'tags': project.tags,
                        'user_id': str(project.user.id) if project.user else None,
                        'date_created': project.date_created.isoformat() if project.date_created else None,
                        'date_updated': project.date_updated.isoformat() if project.date_updated else None
                    }
                })
            else:
                # List all projects
                projects = Project.objects.all()
                project_list = [{
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': project.tags,
                    'user_id': str(project.user.id) if project.user else None,
                    'date_created': project.date_created.isoformat() if project.date_created else None,
                    'date_updated': project.date_updated.isoformat() if project.date_updated else None
                } for project in projects]
                
                return JsonResponse({'status': 'success', 'projects': project_list, 'count': len(project_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # POST - Create project
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            name = data.get('name')
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Name is required'}, status=400)
            
            user_id = data.get('user_id')
            if not user_id:
                return JsonResponse({'status': 'error', 'message': 'user_id is required'}, status=400)
            
            user = User.objects(id=user_id).first()
            if not user:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            
            project = Project(
                name=name,
                description=data.get('description', ''),
                tags=data.get('tags', {}),
                user=user
            )
            project.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Project created',
                'project': {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': project.tags,
                    'user_id': str(user.id)
                }
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # PUT - Update project
    def put(self, request, project_id):
        try:
            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
            
            data = json.loads(request.body)
            
            if 'name' in data:
                project.name = data['name']
            if 'description' in data:
                project.description = data['description']
            if 'tags' in data:
                project.tags = data['tags']
            if 'user_id' in data:
                if data['user_id']:
                    user = User.objects(id=data['user_id']).first()
                    if not user:
                        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
                    project.user = user
                else:
                    project.user = None
            
            project.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Project updated',
                'project': {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': project.tags,
                    'user_id': str(project.user.id) if project.user else None
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # DELETE - Delete project
    def delete(self, request, project_id):
        try:
            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
            
            project.delete()
            return JsonResponse({'status': 'success', 'message': 'Project deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class TagView(View):
    # GET - List all tags or get specific tag
    def get(self, request, tag_id=None):
        try:
            if tag_id:
                # Get specific tag
                tag = Tag.objects(id=tag_id).first()
                if not tag:
                    return JsonResponse({'status': 'error', 'message': 'Tag not found'}, status=404)
                
                return JsonResponse({
                    'status': 'success',
                    'tag': {
                        'id': str(tag.id),
                        'numeric_id': tag.numeric_id,
                        'name': tag.name
                    }
                })
            else:
                # List all tags
                tags = Tag.objects.all()
                tag_list = [{
                    'id': str(tag.id),
                    'numeric_id': tag.numeric_id,
                    'name': tag.name
                } for tag in tags]
                
                return JsonResponse({'status': 'success', 'tags': tag_list, 'count': len(tag_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # POST - Create tag
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            numeric_id = data.get('numeric_id')
            name = data.get('name')
            
            if numeric_id is None or not name:
                return JsonResponse({'status': 'error', 'message': 'numeric_id and name are required'}, status=400)
            
            # Check if numeric_id already exists
            if Tag.objects(numeric_id=numeric_id).first():
                return JsonResponse({'status': 'error', 'message': 'Tag with this numeric_id already exists'}, status=400)
            
            tag = Tag(
                numeric_id=numeric_id,
                name=name
            )
            tag.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Tag created',
                'tag': {
                    'id': str(tag.id),
                    'numeric_id': tag.numeric_id,
                    'name': tag.name
                }
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # PUT - Update tag
    def put(self, request, tag_id):
        try:
            tag = Tag.objects(id=tag_id).first()
            if not tag:
                return JsonResponse({'status': 'error', 'message': 'Tag not found'}, status=404)
            
            data = json.loads(request.body)
            
            if 'numeric_id' in data:
                # Check if numeric_id is taken by another tag
                existing = Tag.objects(numeric_id=data['numeric_id'], id__ne=tag_id).first()
                if existing:
                    return JsonResponse({'status': 'error', 'message': 'numeric_id already exists'}, status=400)
                tag.numeric_id = data['numeric_id']
            if 'name' in data:
                tag.name = data['name']
            
            tag.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Tag updated',
                'tag': {
                    'id': str(tag.id),
                    'numeric_id': tag.numeric_id,
                    'name': tag.name
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # DELETE - Delete tag
    def delete(self, request, tag_id):
        try:
            tag = Tag.objects(id=tag_id).first()
            if not tag:
                return JsonResponse({'status': 'error', 'message': 'Tag not found'}, status=404)
            
            tag.delete()
            return JsonResponse({'status': 'success', 'message': 'Tag deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class S3View(View):
    def __init__(self):
        super().__init__()
        self.s3_service = S3Service()
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            bucket_name = data.get('bucket_name', 'test-bucket')
            key = data.get('key', 'test-file')
            content = data.get('content', 'Hello S3!')
            project_id = data.get('project_id')
            tag_ids = data.get('tag_ids', [])
            
            self.s3_service.create_bucket(bucket_name)
            metadata = self.s3_service.upload_file(bucket_name, key, content)
            
            # Create tag references with numeric_id for ordering
            tag_references = []
            for tag_id in tag_ids:
                tag = Tag.objects(id=tag_id).first()
                if tag:
                    tag_references.append(TagReference(tag_id=tag, numeric_id=tag.numeric_id))
            
            # Save image metadata to MongoDB
            image = Image(
                path=metadata['path'],
                bucket_name=bucket_name,
                key=key,
                size=metadata['size'],
                format=key.split('.')[-1] if '.' in key else 'unknown',
                content_type=metadata['content_type'],
                etag=metadata['etag'],
                last_modified=metadata['last_modified'],
                project=project_id if project_id else None,
                tag_references=tag_references
            )
            image.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'File uploaded to S3',
                'image_id': str(image.id),
                'metadata': metadata
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
