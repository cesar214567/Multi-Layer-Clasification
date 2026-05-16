import os
import zipfile
import io

# Must be set before TensorFlow is imported anywhere (suppresses GPU/TRT library warnings on CPU-only machines)
#os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')

from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .services import S3Service
from .models import User, Project, Image, Tag, TagReference, TrainedModel, TrainedModelReference, PreTrainedModel, PreTrainedModelReference, PreTrainedDetectionModel, PreTrainedDetectionModelReference, ProjectReference, ModelVersion
import json
from bson import ObjectId
from functools import wraps
from ultralytics import YOLO

def resolve_tag_references(tags_data,project = None):
    """
    Resolve a list of tag dicts into TagReference embedded documents.

    Each item may contain:
      - {"tag_id": "<ObjectId str>", "name": "<str>"}  → look up Tag by id; create if missing
      - {"name": "<str>", "project_id": "<str>"}       → look up Tag by name + project; create if missing
    Optional fields: "project_id"

    Tag uniqueness is scoped to (name, project): two tags with the same name can
    coexist in different projects.
    """
    tag_references = []
    for item in tags_data:
        name = item.get('name')
        tag_id_str = item.get('tag_id')
        if not name:
            continue  # skip malformed entries without a name
        if tag_id_str:
            tag = Tag.objects(id=tag_id_str).first()
            if not tag:
                tag = Tag(name=name, project=project)
                tag.save()
        else:
            # Look up by both name AND project (None project is also a valid scope)
            tag = Tag.objects(name=name, project=project).first()
            if not tag:
                tag = Tag(name=name, project=project)
                tag.save()
        tag_references.append(TagReference(tag_id=tag, name=tag.name))

    return tag_references


def serialize_tag_references(tag_refs):
    """Serialize a list of TagReference embedded documents to JSON-safe dicts."""
    result = []
    for tr in tag_refs:
        try:
            result.append({'tag_id': str(tr.tag_id.id), 'name': tr.name})
        except Exception:
            result.append({'tag_id': None, 'name': tr.name})
    return result


def resolve_trained_model_references(models_data):
    """
    Resolve a list of trained-model dicts into TrainedModelReference embedded documents.

    Each item may contain:
      - {"model_id": "<ObjectId str>", "name": "<str>"}  → look up TrainedModel by id
      - {"name": "<str>"}                                → look up TrainedModel by name; create if missing
    Optional field: "description"
    """
    references = []
    for item in models_data:
        name = item.get('name')
        model_id_str = item.get('model_id')
        description = item.get('description', '')

        if not name:
            continue

        if model_id_str:
            model = TrainedModel.objects(id=model_id_str).first()
            if not model:
                model = TrainedModel(name=name, description=description)
                model.save()
        else:
            model = TrainedModel.objects(name=name).first()
            if not model:
                model = TrainedModel(name=name, description=description)
                model.save()

        references.append(TrainedModelReference(
            model_id=model,
            name=model.name,
            description=model.description or '',
        ))

    return references


def serialize_trained_model_references(model_refs):
    """Serialize a list of TrainedModelReference embedded documents to JSON-safe dicts."""
    result = []
    for mr in model_refs:
        try:
            result.append({
                'model_id': str(mr.model_id.id),
                'name': mr.name,
                'description': mr.description,
            })
        except Exception:
            result.append({'model_id': None, 'name': mr.name, 'description': mr.description})
    return result


def resolve_pretrained_model_references(models_data):
    """
    Resolve a list of pretrained-model dicts into PreTrainedModelReference embedded documents.

    Each item may contain:
      - {"model_id": "<ObjectId str>", "name": "<str>"}  → look up PreTrainedModel by id
      - {"name": "<str>", "path": "<str>"}               → look up PreTrainedModel by name; create if missing
    Optional field: "description"
    """
    references = []
    for item in models_data:
        name = item.get('name')
        model_id_str = item.get('model_id')
        description = item.get('description', '')

        if not name:
            continue

        if model_id_str:
            model = PreTrainedModel.objects(id=model_id_str).first()
            if not model:
                path = item.get('path', '')
                model = PreTrainedModel(name=name, description=description, path=path)
                model.save()
        else:
            model = PreTrainedModel.objects(name=name).first()
            if not model:
                path = item.get('path', '')
                model = PreTrainedModel(name=name, description=description, path=path)
                model.save()

        references.append(PreTrainedModelReference(
            model_id=model,
            name=model.name,
            description=model.description or '',
        ))

    return references


def serialize_pretrained_model_references(model_refs):
    """Serialize a list of PreTrainedModelReference embedded documents to JSON-safe dicts."""
    result = []
    for mr in model_refs:
        try:
            result.append({
                'model_id': str(mr.model_id.id),
                'name': mr.name,
                'description': mr.description,
            })
        except Exception:
            result.append({'model_id': None, 'name': mr.name, 'description': mr.description})
    return result

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
                    'tags': serialize_tag_references(project.tags),
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
    def _serialize_user(self, user):
        return {
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'projects': [{
                'id': str(ref.project_id.id),
                'name': ref.name,
            } for ref in (user.projects or [])],
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_active': user.is_active,
        }

    def get(self, request, user_id=None):
        try:
            if user_id:
                user = User.objects(id=user_id).first()
                if not user:
                    return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
                return JsonResponse({'status': 'success', 'user': self._serialize_user(user)})
            else:
                users = User.objects.all()
                user_list = [self._serialize_user(u) for u in users]
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
            def serialize_project(project):
                return {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': serialize_tag_references(project.tags),
                    'trained_models': serialize_trained_model_references(project.trained_models),
                    'pretrained_models': serialize_pretrained_model_references(project.pretrained_models),
                    'pretrained_detection_models': serialize_pretrained_model_references(project.pretrained_detection_models),
                    'user_id': str(project.user.id) if project.user else None,
                    'date_created': project.date_created.isoformat() if project.date_created else None,
                    'date_updated': project.date_updated.isoformat() if project.date_updated else None,
                }

            if project_id:
                project = Project.objects(id=project_id).first()
                if not project:
                    return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
                return JsonResponse({'status': 'success', 'project': serialize_project(project)})
            else:
                projects = Project.objects.all()
                project_list = [serialize_project(p) for p in projects]
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
                user=user
            )
            project.save()
            # Re-resolve tags scoped to this project now that it has an ID
            tags_data = data.get('tags', [])
            if tags_data:
                scoped = [dict(item, project_id=str(project.id)) for item in tags_data]
                project.tags = resolve_tag_references(scoped,project)
                project.save()

            # Add ProjectReference to the user
            user.projects.append(ProjectReference(project_id=project, name=project.name))
            user.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Project created',
                'project': {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': serialize_tag_references(project.tags),
                    'trained_models': serialize_trained_model_references(project.trained_models),
                    'pretrained_models': serialize_pretrained_model_references(project.pretrained_models),
                    'pretrained_detection_models': serialize_pretrained_model_references(project.pretrained_detection_models),
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
                project.tags = resolve_tag_references(data['tags'],project)
            if 'trained_models' in data:
                project.trained_models = resolve_trained_model_references(data['trained_models'])
            if 'pretrained_models' in data:
                project.pretrained_models = resolve_pretrained_model_references(data['pretrained_models'])
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
                    'tags': serialize_tag_references(project.tags),
                    'trained_models': serialize_trained_model_references(project.trained_models),
                    'pretrained_models': serialize_pretrained_model_references(project.pretrained_models),
                    'pretrained_detection_models': serialize_pretrained_model_references(project.pretrained_detection_models),
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
                        'name': tag.name,
                        'project_id': str(tag.project.id) if tag.project else None,
                    }
                })
            else:
                # List all tags
                tags = Tag.objects.all()
                tag_list = [{
                    'id': str(tag.id),
                    'name': tag.name,
                    'project_id': str(tag.project.id) if tag.project else None,
                } for tag in tags]

                return JsonResponse({'status': 'success', 'tags': tag_list, 'count': len(tag_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST - Create tag
    def post(self, request):
        try:
            data = json.loads(request.body)

            name = data.get('name')
            if not name:
                return JsonResponse({'status': 'error', 'message': 'name is required'}, status=400)

            project_id = data.get('project_id')

            project = None
            if project_id:
                project = Project.objects(id=project_id).first()
                if not project:
                    return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

            # Check if tag with same name already exists within the same project scope
            if Tag.objects(name=name, project=project).first():
                return JsonResponse({'status': 'error', 'message': 'Tag with this name already exists'}, status=400)

            tag = Tag(name=name, project=project)
            tag.save()

            # Add tag reference to the project's tags list
            if project:
                project.tags.append(TagReference(tag_id=tag, name=tag.name))
                project.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Tag created',
                'tag': {
                    'id': str(tag.id),
                    'name': tag.name,
                    'project_id': str(tag.project.id) if tag.project else None,
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

            if 'name' in data:
                # Check if name is taken by another tag in the same project scope
                existing = Tag.objects(name=data['name'], project=tag.project, id__ne=tag_id).first()
                if existing:
                    return JsonResponse({'status': 'error', 'message': 'Tag with this name already exists'}, status=400)
                tag.name = data['name']

            if 'project_id' in data:
                if data['project_id']:
                    project = Project.objects(id=data['project_id']).first()
                    if not project:
                        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
                    tag.project = project
                else:
                    tag.project = None

            tag.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Tag updated',
                'tag': {
                    'id': str(tag.id),
                    'name': tag.name,
                    'project_id': str(tag.project.id) if tag.project else None,
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
class PreTrainedModelView(View):
    # GET - List all pretrained models or get specific model
    def get(self, request, model_id=None):
        try:
            if model_id:
                model = PreTrainedModel.objects(id=model_id).first()
                if not model:
                    return JsonResponse({'status': 'error', 'message': 'PreTrainedModel not found'}, status=404)

                return JsonResponse({
                    'status': 'success',
                    'pretrained_model': {
                        'id': str(model.id),
                        'name': model.name,
                        'description': model.description,
                        'path': model.path,
                        'format': model.format,
                        'size': model.size,
                        'date_created': model.date_created.isoformat() if model.date_created else None,
                        'date_updated': model.date_updated.isoformat() if model.date_updated else None,
                    }
                })
            else:
                models = PreTrainedModel.objects.all()
                model_list = [{
                    'id': str(m.id),
                    'name': m.name,
                    'description': m.description,
                    'path': m.path,
                    'format': m.format,
                    'size': m.size,
                    'date_created': m.date_created.isoformat() if m.date_created else None,
                    'date_updated': m.date_updated.isoformat() if m.date_updated else None,
                } for m in models]

                return JsonResponse({'status': 'success', 'pretrained_models': model_list, 'count': len(model_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST - Attach an existing PreTrainedModel to a project, OR build a new one from scratch
    def post(self, request):
        import tempfile
        import tensorflow as tf
        import tensorflow.keras as keras
        try:
            data = json.loads(request.body)

            # ------------------------------------------------------------------
            # MODE A: attach_existing=true  →  link an already-created model to
            #         a project without re-building or re-uploading anything.
            #
            # Lookup strategy (in priority order):
            #   1. pretrained_model_id  – direct MongoDB ObjectId lookup
            #   2. architecture + dataset  – compound name lookup
            #      (name is stored as "{Architecture}_{dataset}", e.g. "VGG19_imagenet")
            #
            # Required in all cases: project_id
            # ------------------------------------------------------------------
            project_id = data.get('project_id')
            architecture = data.get('architecture')
            dataset = data.get('dataset', 'imagenet')
            bucket_name = 'pretrained-models'
            available = [k for k in dir(keras.applications) if not k.startswith('_')]
            arch_key = architecture.lower().replace('-', '').replace('_', '')
            matched_arch = next(
                (a for a in available if a.lower().replace('-', '').replace('_', '') == arch_key),
                None,
            )
            project = Project.objects(id=project_id).first()
            if not architecture:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': (
                            'Either architecture or dataset (+ optional dataset) '
                            'is required when attach_existing is true'
                        ),
                    },
                    status=400,
                )
            if not project_id:
                return JsonResponse(
                    {'status': 'error', 'message': 'project was not found'},
                    status=400,
                )
            
            if matched_arch is None:
                return JsonResponse(
                    {'status': 'error', 'message': f'Unknown architecture "{matched_arch}"'},
                    status=400,
                )
            if project is None:
                return JsonResponse(
                    {'status': 'error', 'message': f'Project not found'},
                    status=400,
                )
            
            compound_name = f'{matched_arch}_{dataset.lower()}'
            pretrained_model = PreTrainedModel.objects(name=compound_name).first()
            if pretrained_model:
                # Check if the model is already attached to this project (avoid duplicates)
                already_attached = any(
                    str(ref.name) == str(pretrained_model.name) for ref in project.pretrained_models
                )
                if already_attached:
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': f'PreTrainedModel "{pretrained_model.name}" is already attached to project "{project.name}"',
                        },
                        status=400,
                    )

                # Attach the model to the project
                project.pretrained_models.append(
                    PreTrainedModelReference(
                        model_id=pretrained_model,
                        name=pretrained_model.name,
                        description=pretrained_model.description or '',
                    )
                )
                project.save()

                return JsonResponse(
                    {
                        'status': 'success',
                        'message': f'PreTrainedModel "{pretrained_model.name}" attached to project "{project.name}"',
                        'pretrained_model': {
                            'id': str(pretrained_model.id),
                            'name': pretrained_model.name,
                            'description': pretrained_model.description,
                            'path': pretrained_model.path,
                            'format': pretrained_model.format,
                            'size': pretrained_model.size,
                            'enabled': pretrained_model.enabled,
                            'date_created': pretrained_model.date_created.isoformat() if pretrained_model.date_created else None,
                            'date_updated': pretrained_model.date_updated.isoformat() if pretrained_model.date_updated else None,
                        },
                        'project_id': str(project.id),
                    },
                    status=200,
                )
            else: 
                # ------------------------------------------------------------------
                # MODE B: build a new Keras model from scratch and upload to S3
                # ------------------------------------------------------------------
                # --- Build Keras model ---
                # List of available architecture names from keras.applications

                arch_class = getattr(keras.applications, matched_arch)

                # Use weights=dataset if keras supports it (imagenet), else weights=None
                keras_supported_weights = {'imagenet'}
                weights = dataset.lower() if dataset.lower() in keras_supported_weights else None

                keras_model = arch_class(weights=weights, include_top=True)

                # --- Save model to a temp file and read bytes ---
                with tempfile.NamedTemporaryFile(suffix='.weights.h5', delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    keras_model.save_weights(tmp_path)
                    file_size = os.path.getsize(tmp_path)
                    with open(tmp_path, 'rb') as f:
                        model_bytes = f.read()
                finally:
                    os.unlink(tmp_path)

                # --- Upload to S3 (LocalStack) ---
                s3_service = S3Service()
                s3_service.create_bucket(bucket_name)

                weights_label = dataset.lower() if weights else 'random'

                # Resolve name/description BEFORE building the S3 key (model_name is used in s3_key)
                model_name = f'{matched_arch}_{weights_label}'
                description = data.get('description') or (
                    f'{matched_arch} pretrained on {dataset} (Keras {keras.__version__}, TF {tf.__version__})'
                )

                s3_key = f'trained-models/{model_name}.weights.h5'

                metadata = s3_service.upload_file(bucket_name, s3_key, model_bytes)

                # --- Persist PreTrainedModel document (size comes from the generated file) ---
                pretrained_model = PreTrainedModel(
                    name=model_name,
                    description=description,
                    path=metadata['path'],
                    format='h5',
                    size=file_size,
                    enabled = True,
                )
                pretrained_model.save()

                # --- Optionally attach to a Project ---
                project_id = data.get('project_id')
                project = None
                if project_id:
                    project = Project.objects(id=project_id).first()
                    if not project:
                        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
                    project.pretrained_models.append(
                        PreTrainedModelReference(
                            model_id=pretrained_model,
                            name=pretrained_model.name,
                            description=pretrained_model.description or '',
                        )
                    )
                    project.save()

                response_data = {
                    'id': str(pretrained_model.id),
                    'name': pretrained_model.name,
                    'description': pretrained_model.description,
                    'path': pretrained_model.path,
                    'format': pretrained_model.format,
                    'size': pretrained_model.size,
                    'architecture': matched_arch,
                    'dataset': dataset,
                    'weights_used': weights or 'random (dataset not supported by Keras)',
                    's3_bucket': bucket_name,
                    's3_key': s3_key,
                    'date_created': pretrained_model.date_created.isoformat() if pretrained_model.date_created else None,
                    'date_updated': pretrained_model.date_updated.isoformat() if pretrained_model.date_updated else None,
                }
                if project:
                    response_data['project_id'] = str(project.id)

                return JsonResponse({
                    'status': 'success',
                    'message': 'PreTrainedModel built and uploaded to S3',
                    'pretrained_model': response_data,
                }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # PUT - Update pretrained model
    def put(self, request, model_id):
        try:
            model = PreTrainedModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedModel not found'}, status=404)

            data = json.loads(request.body)

            if 'name' in data:
                model.name = data['name']
            if 'description' in data:
                model.description = data['description']
            model.save()

            return JsonResponse({
                'status': 'success',
                'message': 'PreTrainedModel updated',
                'pretrained_model': {
                    'id': str(model.id),
                    'name': model.name,
                    'description': model.description,
                    'path': model.path,
                    'format': model.format,
                    'size': model.size,
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # DELETE - Delete pretrained model
    def delete(self, request, model_id):
        try:
            model = PreTrainedModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedModel not found'}, status=404)

            model.delete()
            return JsonResponse({'status': 'success', 'message': 'PreTrainedModel deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# All YOLO pretrained model filenames mapped to their valid datasets
YOLO_MODELS = {
    # Detection - COCO
    'yolov3u': {'coco'}, 'yolov3-sppu': {'coco'}, 'yolov3-tinyu': {'coco'},
    'yolov5nu': {'coco'}, 'yolov5su': {'coco'}, 'yolov5mu': {'coco'}, 'yolov5lu': {'coco'}, 'yolov5xu': {'coco'},
    'yolov5n6u': {'coco'}, 'yolov5s6u': {'coco'}, 'yolov5m6u': {'coco'}, 'yolov5l6u': {'coco'}, 'yolov5x6u': {'coco'},
    'yolov8n': {'coco'}, 'yolov8s': {'coco'}, 'yolov8m': {'coco'}, 'yolov8l': {'coco'}, 'yolov8x': {'coco'},
    'yolov9t': {'coco'}, 'yolov9s': {'coco'}, 'yolov9m': {'coco'}, 'yolov9c': {'coco'}, 'yolov9e': {'coco'},
    'yolov10n': {'coco'}, 'yolov10s': {'coco'}, 'yolov10m': {'coco'}, 'yolov10b': {'coco'}, 'yolov10l': {'coco'}, 'yolov10x': {'coco'},
    'yolo11n': {'coco'}, 'yolo11s': {'coco'}, 'yolo11m': {'coco'}, 'yolo11l': {'coco'}, 'yolo11x': {'coco'},
    'yolo12n': {'coco'}, 'yolo12s': {'coco'}, 'yolo12m': {'coco'}, 'yolo12l': {'coco'}, 'yolo12x': {'coco'},
    'yolo26n': {'coco'}, 'yolo26s': {'coco'}, 'yolo26m': {'coco'}, 'yolo26l': {'coco'}, 'yolo26x': {'coco'},
    'rtdetr-l': {'coco'}, 'rtdetr-x': {'coco'},
    # Detection - Open Images V7
    'yolov8n-oiv7': {'open-images-v7'}, 'yolov8s-oiv7': {'open-images-v7'}, 'yolov8m-oiv7': {'open-images-v7'}, 'yolov8l-oiv7': {'open-images-v7'}, 'yolov8x-oiv7': {'open-images-v7'},
    # Detection - Open Vocabulary (World)
    'yolov8s-world': {'open-vocabulary'}, 'yolov8m-world': {'open-vocabulary'}, 'yolov8l-world': {'open-vocabulary'}, 'yolov8x-world': {'open-vocabulary'},
    'yolov8s-worldv2': {'open-vocabulary-v2'}, 'yolov8m-worldv2': {'open-vocabulary-v2'}, 'yolov8l-worldv2': {'open-vocabulary-v2'}, 'yolov8x-worldv2': {'open-vocabulary-v2'},
    # Segmentation - COCO
    'yolov8n-seg': {'coco'}, 'yolov8s-seg': {'coco'}, 'yolov8m-seg': {'coco'}, 'yolov8l-seg': {'coco'}, 'yolov8x-seg': {'coco'},
    'yolov9c-seg': {'coco'}, 'yolov9e-seg': {'coco'},
    'yolo11n-seg': {'coco'}, 'yolo11s-seg': {'coco'}, 'yolo11m-seg': {'coco'}, 'yolo11l-seg': {'coco'}, 'yolo11x-seg': {'coco'},
    'yolo26n-seg': {'coco'}, 'yolo26s-seg': {'coco'}, 'yolo26m-seg': {'coco'}, 'yolo26l-seg': {'coco'}, 'yolo26x-seg': {'coco'},
    # Classification - ImageNet
    'yolov8n-cls': {'imagenet'}, 'yolov8s-cls': {'imagenet'}, 'yolov8m-cls': {'imagenet'}, 'yolov8l-cls': {'imagenet'}, 'yolov8x-cls': {'imagenet'},
    'yolo11n-cls': {'imagenet'}, 'yolo11s-cls': {'imagenet'}, 'yolo11m-cls': {'imagenet'}, 'yolo11l-cls': {'imagenet'}, 'yolo11x-cls': {'imagenet'},
    'yolo26n-cls': {'imagenet'}, 'yolo26s-cls': {'imagenet'}, 'yolo26m-cls': {'imagenet'}, 'yolo26l-cls': {'imagenet'}, 'yolo26x-cls': {'imagenet'},
    # Pose - COCO
    'yolov8n-pose': {'coco'}, 'yolov8s-pose': {'coco'}, 'yolov8m-pose': {'coco'}, 'yolov8l-pose': {'coco'}, 'yolov8x-pose': {'coco'},
    'yolo11n-pose': {'coco'}, 'yolo11s-pose': {'coco'}, 'yolo11m-pose': {'coco'}, 'yolo11l-pose': {'coco'}, 'yolo11x-pose': {'coco'},
    'yolo26n-pose': {'coco'}, 'yolo26s-pose': {'coco'}, 'yolo26m-pose': {'coco'}, 'yolo26l-pose': {'coco'}, 'yolo26x-pose': {'coco'},
    # OBB - DOTAv1
    'yolov8n-obb': {'dota-v1'}, 'yolov8s-obb': {'dota-v1'}, 'yolov8m-obb': {'dota-v1'}, 'yolov8l-obb': {'dota-v1'}, 'yolov8x-obb': {'dota-v1'},
    'yolo11n-obb': {'dota-v1'}, 'yolo11s-obb': {'dota-v1'}, 'yolo11m-obb': {'dota-v1'}, 'yolo11l-obb': {'dota-v1'}, 'yolo11x-obb': {'dota-v1'},
    'yolo26n-obb': {'dota-v1'}, 'yolo26s-obb': {'dota-v1'}, 'yolo26m-obb': {'dota-v1'}, 'yolo26l-obb': {'dota-v1'}, 'yolo26x-obb': {'dota-v1'},
    # SAM
    'sam_b': {'sa-1b'}, 'sam_l': {'sa-1b'}, 'sam2_b': {'sa-1b'}, 'sam2_l': {'sa-1b'}, 'sam2_s': {'sa-1b'}, 'sam2_t': {'sa-1b'},
    'sam2.1_b': {'sa-1b'}, 'sam2.1_l': {'sa-1b'}, 'sam2.1_s': {'sa-1b'}, 'sam2.1_t': {'sa-1b'},
    'FastSAM-s': {'sa-1b'}, 'FastSAM-x': {'sa-1b'}, 'mobile_sam': {'sa-1b'},
    # YOLO NAS
    'yolo_nas_s': {'coco'}, 'yolo_nas_m': {'coco'}, 'yolo_nas_l': {'coco'},
}

YOLO_TASK_MAP = {
    '-seg': 'segment', '-cls': 'classify', '-pose': 'pose', '-obb': 'obb',
    '-world': 'detect', '-worldv2': 'detect', '-oiv7': 'detect',
}


def _resolve_yolo_model(name):
    """Resolve a model name (case-insensitive, with or without .pt) to a valid YOLO model name."""
    clean = name.replace('.pt', '').strip()
    match = next((m for m in YOLO_MODELS if m.lower() == clean.lower()), None)
    return match


def _get_yolo_task(model_name):
    for suffix, task in YOLO_TASK_MAP.items():
        if suffix in model_name:
            return task
    if 'sam' in model_name.lower() or 'SAM' in model_name:
        return 'segment'
    return 'detect'


def _get_yolo_default_dataset(model_name):
    """Return the default (first) dataset for a resolved model name."""
    datasets = YOLO_MODELS.get(model_name, set())
    return next(iter(datasets)) if datasets else 'coco'


def _validate_yolo_dataset(model_name, dataset):
    """Check if the dataset is valid for the given model. Returns (valid, allowed_datasets)."""
    allowed = YOLO_MODELS.get(model_name, set())
    return dataset in allowed, allowed


@method_decorator(csrf_exempt, name='dispatch')
class PreTrainedDetectionModelView(View):
    BUCKET_NAME = 'pretrained-detection-models'

    def _serialize(self, m):
        return {
            'id': str(m.id),
            'name': m.name,
            'description': m.description,
            'path': m.path,
            'format': m.format,
            'size': m.size,
            'architecture': m.architecture,
            'task': m.task,
            'dataset': m.dataset,
            'enabled': m.enabled,
            'date_created': m.date_created.isoformat() if m.date_created else None,
            'date_updated': m.date_updated.isoformat() if m.date_updated else None,
        }

    def get(self, request, model_id=None):
        try:
            if model_id:
                model = PreTrainedDetectionModel.objects(id=model_id).first()
                if not model:
                    return JsonResponse({'status': 'error', 'message': 'PreTrainedDetectionModel not found'}, status=404)
                return JsonResponse({'status': 'success', 'pretrained_detection_model': self._serialize(model)})
            else:
                models = PreTrainedDetectionModel.objects.all()
                model_list = [self._serialize(m) for m in models]
                return JsonResponse({'status': 'success', 'pretrained_detection_models': model_list, 'count': len(model_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def post(self, request):
        """
        Build or attach a YOLO pretrained detection model.

        MODE A (attach_existing=true): attach an already-stored model to a project.
        MODE B (default): download the YOLO model, upload to S3, optionally attach to project.

        Required: model (e.g. "yolov8n", "yolo11l-seg", "yolov8l-oiv7")
        Optional: project_id, description, dataset (validated against model)
        """
        import tempfile
        try:
            data = json.loads(request.body)
            model_name_raw = data.get('model')
            project_id = data.get('project_id')
            dataset_input = data.get('dataset')

            if not model_name_raw:
                return JsonResponse({'status': 'error', 'message': 'model is required'}, status=400)

            matched = _resolve_yolo_model(model_name_raw)
            if not matched:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Unknown YOLO model "{model_name_raw}". Use GET /api/pretrained-detection-models/ to list available models or check the documentation.',
                }, status=400)

            pt_filename = f'{matched}.pt'
            task = _get_yolo_task(matched)

            # Dataset: use provided value or fall back to default for this model
            if dataset_input:
                valid, allowed = _validate_yolo_dataset(matched, dataset_input)
                if not valid:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Invalid dataset "{dataset_input}" for model "{matched}". Valid datasets: {sorted(allowed)}',
                    }, status=400)
                dataset = dataset_input
            else:
                dataset = _get_yolo_default_dataset(matched)

            project = None
            if project_id:
                project = Project.objects(id=project_id).first()
                if not project:
                    return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
            # MODE B: check if already built
            existing = PreTrainedDetectionModel.objects(name=matched).first()
            if existing:
                # Already in S3, just attach to project if provided
                if project:
                    already = any(str(ref.name) == matched for ref in project.pretrained_detection_models)
                    if already:
                        return JsonResponse({'status': 'error', 'message': f'"{matched}" is already attached to project "{project.name}"'}, status=400)
                    project.pretrained_detection_models.append(
                        PreTrainedDetectionModelReference(model_id=existing, name=existing.name, description=existing.description or '')
                    )
                    project.save()
                resp = self._serialize(existing)
                if project:
                    resp['project_id'] = str(project.id)
                return JsonResponse({'status': 'success', 'message': f'"{matched}" already exists, attached to project', 'pretrained_detection_model': resp})

            # Download via ultralytics
            with tempfile.TemporaryDirectory() as tmpdir:
                model_path = os.path.join(tmpdir, pt_filename)
                yolo_model = YOLO(pt_filename)
                # ultralytics downloads to cwd; move if needed
                if os.path.exists(pt_filename) and not os.path.exists(model_path):
                    os.rename(pt_filename, model_path)
                elif not os.path.exists(model_path):
                    model_path = pt_filename

                file_size = os.path.getsize(model_path)
                with open(model_path, 'rb') as f:
                    model_bytes = f.read()

            # Upload to S3
            s3_service = S3Service()
            s3_service.create_bucket(self.BUCKET_NAME)
            s3_key = f'{matched}/{pt_filename}'
            metadata = s3_service.upload_file(self.BUCKET_NAME, s3_key, model_bytes)

            description = data.get('description') or f'YOLO {matched} pretrained on {dataset} ({task})'

            detection_model = PreTrainedDetectionModel(
                name=matched,
                description=description,
                path=metadata['path'],
                format='pt',
                size=file_size,
                architecture=matched,
                task=task,
                dataset=dataset,
                enabled=True,
            )
            detection_model.save()

            if project:
                project.pretrained_detection_models.append(
                    PreTrainedDetectionModelReference(model_id=detection_model, name=detection_model.name, description=detection_model.description or '')
                )
                project.save()

            resp = self._serialize(detection_model)
            resp['s3_bucket'] = self.BUCKET_NAME
            resp['s3_key'] = s3_key
            if project:
                resp['project_id'] = str(project.id)

            return JsonResponse({'status': 'success', 'message': f'YOLO model "{matched}" downloaded and uploaded to S3', 'pretrained_detection_model': resp}, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def put(self, request, model_id):
        try:
            model = PreTrainedDetectionModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedDetectionModel not found'}, status=404)
            data = json.loads(request.body)
            if 'name' in data:
                model.name = data['name']
            if 'description' in data:
                model.description = data['description']
            if 'enabled' in data:
                model.enabled = data['enabled']
            model.save()
            return JsonResponse({'status': 'success', 'message': 'PreTrainedDetectionModel updated', 'pretrained_detection_model': self._serialize(model)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def delete(self, request, model_id):
        try:
            model = PreTrainedDetectionModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedDetectionModel not found'}, status=404)
            model.delete()
            return JsonResponse({'status': 'success', 'message': 'PreTrainedDetectionModel deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ──────────────────────────────────────────────────────────────────────────────
# PreTrained Detection Model Inference  (YOLO — all tasks)
# ──────────────────────────────────────────────────────────────────────────────
# Supported tasks and what each produces:
#   detect        → bounding boxes  (x1, y1, x2, y2, confidence, class)
#   segment       → bounding boxes  + per-instance binary masks
#   classify      → class probabilities (no spatial output)
#   pose          → bounding boxes  + keypoints (x, y, visible) per person
#   obb           → oriented boxes  (x, y, w, h, angle, confidence, class)
# ──────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class PreTrainedDetectionModelInferenceView(View):

    def post(self, request):
        """
        Run inference with a YOLO pretrained detection model.

        Accepts multipart/form-data:
            - pretrained_detection_model_id  (required)
            - image                          (required, file upload)
            - confidence                     (optional, float 0-1, default 0.25)

        Returns a ZIP containing:
            results.json              — structured predictions (schema varies by task)
            annotated/<filename>      — image with visual overlays drawn by Ultralytics
            crops/crop_<i>.png        — cropped detections from the original image
            masks/mask_<i>.png        — (segmentation only) raw binary mask PNGs
            crops/ for segmentation   — background-removed crops using the instance mask
        """
        import io
        import zipfile
        import tempfile
        import numpy as np

        try:
            # ── 1. Validate inputs ───────────────────────────────────────────
            model_id = request.POST.get('pretrained_detection_model_id')
            image_file = request.FILES.get('image')
            confidence = float(request.POST.get('confidence', 0.25))

            if not model_id:
                return JsonResponse({'status': 'error', 'message': 'pretrained_detection_model_id is required'}, status=400)
            if not image_file:
                return JsonResponse({'status': 'error', 'message': 'image is required'}, status=400)

            detection_model = PreTrainedDetectionModel.objects(id=model_id).first()
            if not detection_model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedDetectionModel not found'}, status=404)
            if not detection_model.enabled:
                return JsonResponse({'status': 'error', 'message': 'Model is disabled'}, status=400)

            task = detection_model.task  # detect | segment | classify | pose | obb

            # ── 2. Download .pt weights from S3 ─────────────────────────────
            s3 = S3Service()
            s3_path = detection_model.path
            bucket = s3_path.split('/')[2]
            key = '/'.join(s3_path.split('/')[3:])
            weights_bytes = s3.download_file(bucket, key)

            # ── 3. Load YOLO model from weights ─────────────────────────────
            from ultralytics import YOLO
            from PIL import Image as PILImage

            with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
                tmp.write(weights_bytes)
                tmp_path = tmp.name

            try:
                yolo_model = YOLO(tmp_path)

                # ── 4. Save uploaded image to a temp file ────────────────────
                img_name = image_file.name or 'image.jpg'
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(img_name)[1] or '.jpg', delete=False) as img_tmp:
                    for chunk in image_file.chunks():
                        img_tmp.write(chunk)
                    img_tmp_path = img_tmp.name

                # Load original image as RGB numpy array for cropping
                orig_pil = PILImage.open(img_tmp_path).convert('RGBA')
                orig_rgb = PILImage.open(img_tmp_path).convert('RGB')
                orig_np = np.array(orig_rgb)

                # ── 5. Run inference ─────────────────────────────────────────
                results = yolo_model.predict(source=img_tmp_path, conf=confidence, verbose=False)
                result = results[0]

                # ── 6. Build predictions + crop images (task-specific) ───────
                predictions = []
                crop_images = []  # list of (filename, PIL image) tuples

                # ── DETECTION ────────────────────────────────────────────────
                # Each detection: bounding box crop from the original image.
                if task == 'detect':
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        predictions.append({
                            'box': box.xyxy[0].tolist(),
                            'confidence': float(box.conf[0]),
                            'class_id': int(box.cls[0]),
                            'class_name': result.names[int(box.cls[0])],
                            'crop_file': f'crops/crop_{i}.png',
                        })
                        # Crop the bounding box region from the original image
                        crop = orig_rgb.crop((x1, y1, x2, y2))
                        crop_images.append((f'crops/crop_{i}.png', crop))

                # ── SEGMENTATION ─────────────────────────────────────────────
                # Crop uses the instance mask to remove background (transparent).
                elif task == 'segment':
                    masks_data = result.masks
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        pred = {
                            'box': box.xyxy[0].tolist(),
                            'confidence': float(box.conf[0]),
                            'class_id': int(box.cls[0]),
                            'class_name': result.names[int(box.cls[0])],
                            'mask_file': f'masks/mask_{i}.png' if masks_data is not None else None,
                            'crop_file': f'crops/crop_{i}.png',
                        }
                        predictions.append(pred)

                        if masks_data is not None and i < len(masks_data.data):
                            # Resize mask to original image dimensions
                            mask_tensor = masks_data.data[i].cpu().numpy()
                            mask_resized = np.array(PILImage.fromarray((mask_tensor * 255).astype('uint8')).resize(
                                (orig_np.shape[1], orig_np.shape[0]), PILImage.NEAREST
                            ))
                            # Apply mask as alpha channel → background becomes transparent
                            crop_rgba = orig_pil.copy()
                            alpha = np.array(crop_rgba.split()[3])
                            alpha[mask_resized < 128] = 0
                            crop_rgba.putalpha(PILImage.fromarray(alpha))
                            # Crop to bounding box
                            crop = crop_rgba.crop((x1, y1, x2, y2))
                            crop_images.append((f'crops/crop_{i}.png', crop))
                        else:
                            # Fallback: simple box crop if mask unavailable
                            crop = orig_rgb.crop((x1, y1, x2, y2))
                            crop_images.append((f'crops/crop_{i}.png', crop))

                # ── CLASSIFICATION ───────────────────────────────────────────
                # No spatial output — just top-N class probabilities.
                # No crops for classification (whole image is the input).
                elif task == 'classify':
                    probs = result.probs
                    top5_indices = probs.top5
                    top5_confs = probs.top5conf.tolist()
                    for idx, conf_val in zip(top5_indices, top5_confs):
                        predictions.append({
                            'class_id': idx,
                            'class_name': result.names[idx],
                            'confidence': float(conf_val),
                        })

                # ── POSE ESTIMATION ──────────────────────────────────────────
                # Each person: bounding box crop + keypoints.
                elif task == 'pose':
                    keypoints_data = result.keypoints
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        pred = {
                            'box': box.xyxy[0].tolist(),
                            'confidence': float(box.conf[0]),
                            'class_id': int(box.cls[0]),
                            'class_name': result.names[int(box.cls[0])],
                            'crop_file': f'crops/crop_{i}.png',
                        }
                        if keypoints_data is not None and i < len(keypoints_data):
                            pred['keypoints'] = keypoints_data[i].data[0].tolist()
                        predictions.append(pred)
                        # Crop the bounding box region
                        crop = orig_rgb.crop((x1, y1, x2, y2))
                        crop_images.append((f'crops/crop_{i}.png', crop))

                # ── ORIENTED BOUNDING BOXES (OBB) ────────────────────────────
                # Rotated crop using the 4 corner points of the oriented box.
                elif task == 'obb':
                    for i, obb_box in enumerate(result.obb):
                        predictions.append({
                            'obb': obb_box.xywhr[0].tolist(),
                            'confidence': float(obb_box.conf[0]),
                            'class_id': int(obb_box.cls[0]),
                            'class_name': result.names[int(obb_box.cls[0])],
                            'crop_file': f'crops/crop_{i}.png',
                        })
                        # Use the 4 corner points to compute an axis-aligned bounding rect
                        corners = obb_box.xyxyxyxy[0].cpu().numpy()  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                        min_x, min_y = int(corners[:, 0].min()), int(corners[:, 1].min())
                        max_x, max_y = int(corners[:, 0].max()), int(corners[:, 1].max())
                        crop = orig_rgb.crop((min_x, min_y, max_x, max_y))
                        crop_images.append((f'crops/crop_{i}.png', crop))

                # ── 7. Build top-3 classes summary ───────────────────────────
                # Aggregate all predictions by class, pick the highest confidence
                # per class, then rank. The #1 class is separated from #2 and #3.
                if task == 'classify':
                    # Classification already has ranked probabilities
                    top3 = predictions[:3]
                    top_class = top3[0] if top3 else None
                    runner_up_classes = top3[1:3]
                else:
                    # For spatial tasks, group by class_name and take max confidence
                    class_best = {}
                    for p in predictions:
                        cname = p.get('class_name', 'unknown')
                        conf = p.get('confidence', 0)
                        if cname not in class_best or conf > class_best[cname]['confidence']:
                            class_best[cname] = {'class_name': cname, 'class_id': p.get('class_id'), 'confidence': conf}
                    ranked = sorted(class_best.values(), key=lambda x: x['confidence'], reverse=True)[:3]
                    top_class = ranked[0] if ranked else None
                    runner_up_classes = ranked[1:3]

                # ── 8. Build the ZIP response ────────────────────────────────
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:

                    # results.json — structured predictions + top-3 summary
                    results_json = json.dumps({
                        'task': task,
                        'model': detection_model.name,
                        'confidence_threshold': confidence,
                        'image': img_name,
                        'prediction_count': len(predictions),
                        'top_class': top_class,
                        'runner_up_classes': runner_up_classes,
                        'predictions': predictions,
                    }, indent=2)
                    zf.writestr('results.json', results_json)

                    # annotated/<filename> — image with visual overlays
                    # Ultralytics plot() works for ALL tasks (boxes, masks, keypoints, obb)
                    annotated_img = result.plot()
                    annotated_pil = PILImage.fromarray(annotated_img[..., ::-1])  # BGR → RGB
                    img_buf = io.BytesIO()
                    annotated_pil.save(img_buf, format='PNG')
                    zf.writestr(f'annotated/{os.path.splitext(img_name)[0]}.png', img_buf.getvalue())

                    # crops/ — cropped detections (all spatial tasks)
                    for crop_name, crop_pil in crop_images:
                        crop_buf = io.BytesIO()
                        crop_pil.save(crop_buf, format='PNG')
                        zf.writestr(crop_name, crop_buf.getvalue())

                    # masks/ — (SEGMENTATION ONLY) raw binary mask PNGs
                    if task == 'segment' and result.masks is not None:
                        for i, mask_tensor in enumerate(result.masks.data):
                            mask_np = (mask_tensor.cpu().numpy() * 255).astype('uint8')
                            mask_pil = PILImage.fromarray(mask_np, mode='L')
                            mask_buf = io.BytesIO()
                            mask_pil.save(mask_buf, format='PNG')
                            zf.writestr(f'masks/mask_{i}.png', mask_buf.getvalue())

                zip_buffer.seek(0)

                # ── 9. Return ZIP as downloadable response ───────────────────
                from django.http import HttpResponse
                response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="inference_{detection_model.name}_{os.path.splitext(img_name)[0]}.zip"'
                return response

            finally:
                for p in [tmp_path, img_tmp_path]:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def _resolve_keras_architecture(name):
    """Return the canonical Keras architecture name or None if not found."""
    import tensorflow.keras as keras
    available = [k for k in dir(keras.applications) if not k.startswith('_')]
    key = name.lower().replace('-', '').replace('_', '')
    return next((a for a in available if a.lower().replace('-', '').replace('_', '') == key), None)


def _resolve_project_tags(tag_ids, project):
    """
    Validate that each tag_id belongs to the given project and return TagReference list.
    Returns (tag_references, error_message).  error_message is None on success.
    """
    project_tags = {str(tr.tag_id.id): tr for tr in (project.tags or [])}
    refs = []
    for tid in tag_ids:
        if tid not in project_tags:
            return None, f'Tag "{tid}" does not belong to project "{project.name}"'
        tr = project_tags[tid]
        refs.append(TagReference(tag_id=tr.tag_id, name=tr.name))
    return refs, None


def _serialize_trained_model(m):
    return {
        'id': str(m.id),
        'name': m.name,
        'description': m.description,
        'project_id': str(m.project.id) if m.project else None,
        'architecture': m.architecture,
        'include_top': m.include_top,
        'custom_top_layers': m.custom_top_layers or [],
        'custom_architecture': m.custom_architecture or [],
        'tags': serialize_tag_references(m.tags or []),
        'epochs': m.epochs,
        'batch_size': m.batch_size,
        'img_size': m.img_size,
        'learning_rate': m.learning_rate,
        'loss': m.loss,
        'metrics': m.metrics or [],
        'current_version': m.current_version,
        'versions': [{
            'version': v.version,
            'path': v.path,
            'format': v.format,
            'size': v.size,
            'architecture': v.architecture,
            'include_top': v.include_top,
            'custom_top_layers': v.custom_top_layers or [],
            'custom_architecture': v.custom_architecture or [],
            'tags': serialize_tag_references(v.tags or []),
            'epochs': v.epochs,
            'batch_size': v.batch_size,
            'img_size': v.img_size,
            'learning_rate': v.learning_rate,
            'loss': v.loss,
            'metrics': v.metrics or [],
            'notes': v.notes,
            'date_created': v.date_created.isoformat() if v.date_created else None,
        } for v in (m.versions or [])],
        'date_created': m.date_created.isoformat() if m.date_created else None,
        'date_updated': m.date_updated.isoformat() if m.date_updated else None,
    }


@method_decorator(csrf_exempt, name='dispatch')
class TrainedModelView(View):
    # GET - List all trained models or get specific model
    def get(self, request, model_id=None):
        try:
            if model_id:
                model = TrainedModel.objects(id=model_id).first()
                if not model:
                    return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)
                return JsonResponse({'status': 'success', 'trained_model': _serialize_trained_model(model)})
            else:
                models = TrainedModel.objects.all()
                model_list = [_serialize_trained_model(m) for m in models]
                return JsonResponse({'status': 'success', 'trained_models': model_list, 'count': len(model_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST - Create trained model
    def post(self, request):
        try:
            data = json.loads(request.body)

            name = data.get('name')
            if not name:
                return JsonResponse({'status': 'error', 'message': 'name is required'}, status=400)

            project_id = data.get('project_id')
            if not project_id:
                return JsonResponse({'status': 'error', 'message': 'project_id is required'}, status=400)
            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

            architecture = data.get('architecture')
            include_top = data.get('include_top', True)
            custom_top_layers = data.get('custom_top_layers', [])
            custom_architecture = data.get('custom_architecture', [])

            # Validate architecture
            if architecture and architecture.lower() != 'custom':
                matched = _resolve_keras_architecture(architecture)
                if not matched:
                    return JsonResponse({'status': 'error', 'message': f'Unknown architecture "{architecture}"'}, status=400)
                architecture = matched
            elif architecture and architecture.lower() == 'custom':
                architecture = 'custom'
                if not custom_architecture:
                    return JsonResponse({'status': 'error', 'message': 'custom_architecture is required when architecture is "custom"'}, status=400)

            # Resolve tags against project
            tag_refs = []
            tag_ids = data.get('tag_ids', [])
            if tag_ids:
                tag_refs, err = _resolve_project_tags(tag_ids, project)
                if err:
                    return JsonResponse({'status': 'error', 'message': err}, status=400)

            # Auto-append output Dense layer if last Dense doesn't match num_classes
            num_classes = len(tag_refs)
            if num_classes:
                for layer_list in (custom_top_layers, custom_architecture):
                    if not layer_list:
                        continue
                    # Check if last Dense already has correct units
                    last_dense_idx = None
                    for i in range(len(layer_list) - 1, -1, -1):
                        if layer_list[i].get('type') == 'Dense':
                            last_dense_idx = i
                            break
                    if last_dense_idx is None or layer_list[last_dense_idx].get('units') != num_classes:
                        layer_list.append({'type': 'Dense', 'units': num_classes, 'activation': 'softmax'})

            model = TrainedModel(
                name=name,
                description=data.get('description', ''),
                project=project,
                architecture=architecture,
                include_top=include_top,
                custom_top_layers=custom_top_layers,
                custom_architecture=custom_architecture,
                tags=tag_refs,
                epochs=data.get('epochs', 10),
                batch_size=data.get('batch_size', 32),
                img_size=data.get('img_size', 224),
                learning_rate=data.get('learning_rate', 1e-3),
                loss=data.get('loss', 'sparse_categorical_crossentropy'),
                metrics=data.get('metrics', ['accuracy']),
                current_version=0,
            )
            model.save()

            # Attach to project
            project.trained_models.append(
                TrainedModelReference(
                    model_id=model,
                    name=model.name,
                    description=model.description or '',
                )
            )
            project.save()

            return JsonResponse({
                'status': 'success',
                'message': 'TrainedModel created',
                'trained_model': _serialize_trained_model(model),
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # PUT - Update trained model (creates a new version)
    def put(self, request, model_id):
        try:
            model = TrainedModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)

            data = json.loads(request.body)

            if 'name' in data:
                model.name = data['name']
            if 'description' in data:
                model.description = data['description']
            
            if 'architecture' in data:
                arch = data['architecture']
                if arch and arch.lower() != 'custom':
                    matched = _resolve_keras_architecture(arch)
                    if not matched:
                        return JsonResponse({'status': 'error', 'message': f'Unknown architecture "{arch}"'}, status=400)
                    model.architecture = matched
                elif arch and arch.lower() == 'custom':
                    model.architecture = 'custom'
                else:
                    model.architecture = arch

            if 'include_top' in data:
                model.include_top = data['include_top']
            if 'custom_top_layers' in data:
                model.custom_top_layers = data['custom_top_layers']
            if 'custom_architecture' in data:
                model.custom_architecture = data['custom_architecture']
            if 'epochs' in data:
                model.epochs = data['epochs']
            if 'batch_size' in data:
                model.batch_size = data['batch_size']
            if 'img_size' in data:
                model.img_size = data['img_size']
            if 'learning_rate' in data:
                model.learning_rate = data['learning_rate']
            if 'loss' in data:
                model.loss = data['loss']
            if 'metrics' in data:
                model.metrics = data['metrics']

            # Resolve tags against project if provided
            tag_refs = None
            tag_ids = data.get('tag_ids')
            if tag_ids is not None:
                project_id = data.get('project_id')
                if not project_id:
                    return JsonResponse({'status': 'error', 'message': 'project_id is required when tag_ids are provided'}, status=400)
                project = Project.objects(id=project_id).first()
                if not project:
                    return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
                tag_refs, err = _resolve_project_tags(tag_ids, project)
                if err:
                    return JsonResponse({'status': 'error', 'message': err}, status=400)
                model.tags = tag_refs

            # Bump version
            model.current_version = (model.current_version or 0) + 1
            model.create_version(notes=data.get('version_notes'), tags=tag_refs if tag_refs is not None else list(model.tags or []))
            model.save()

            return JsonResponse({
                'status': 'success',
                'message': 'TrainedModel updated',
                'trained_model': _serialize_trained_model(model),
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # DELETE - Delete trained model
    def delete(self, request, model_id):
        try:
            model = TrainedModel.objects(id=model_id).first()
            if not model:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)

            model.delete()
            return JsonResponse({'status': 'success', 'message': 'TrainedModel deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TrainModelView(View):
    """
    POST /api/trained-models/train/

    Builds a Keras model from the TrainedModel architecture config, loads training
    images from S3 (project images, tags as labels) using a hybrid tf.data pipeline
    with disk caching, trains the model, uploads weights to S3, and creates a new
    version on the TrainedModel.

    Required JSON fields:
        - trained_model_id: existing TrainedModel id
        - project_id: project whose images will be used for training
    Optional:
        - epochs (default 10), batch_size (default 32), image_size (default 224)
        - learning_rate (default 1e-3)
        - version_notes
    """

    def post(self, request):
        import tempfile
        import tensorflow as tf
        import tensorflow.keras as keras
        import numpy as np

        try:
            data = json.loads(request.body)

            trained_model_id = data.get('trained_model_id')
            project_id = data.get('project_id')
            if not trained_model_id:
                return JsonResponse({'status': 'error', 'message': 'trained_model_id is required'}, status=400)
            if not project_id:
                return JsonResponse({'status': 'error', 'message': 'project_id is required'}, status=400)

            trained_model = TrainedModel.objects(id=trained_model_id).first()
            if not trained_model:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)
            if not trained_model.architecture:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel has no architecture configured'}, status=400)
            if not trained_model.tags or len(trained_model.tags) < 2:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel must have at least 2 tags to train'}, status=400)

            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

            # --- Collect images and labels from trained model tags ---
            s3_keys = []
            bucket_names = []
            label_strings = []
            for tag_ref in trained_model.tags:
                tag_images = Image.objects(project=project, tag_references__tag_id=tag_ref.tag_id)
                for img in tag_images:
                    s3_keys.append(img.key)
                    bucket_names.append(img.bucket_name)
                    label_strings.append(tag_ref.name)

            if not s3_keys:
                return JsonResponse({'status': 'error', 'message': 'No images found for the trained model tags in this project'}, status=400)

            # Build label mapping
            unique_labels = sorted(set(label_strings))
            label_to_idx = {l: i for i, l in enumerate(unique_labels)}
            num_classes = len(trained_model.tags)
            labels = [label_to_idx[l] for l in label_strings]
            # One-hot encode labels
            labels_onehot = tf.keras.utils.to_categorical(labels, num_classes=num_classes).tolist()

            # --- Hyper-parameters ---
            epochs = trained_model.epochs
            batch_size = trained_model.batch_size
            img_size = trained_model.img_size
            lr = trained_model.learning_rate

            # --- Download images from S3 to local disk ---
            s3_service = S3Service()
            cache_dir = tempfile.mkdtemp(prefix='train_cache_')
            local_paths = []
            for i in range(len(s3_keys)):
                img_bytes = s3_service.download_file(bucket_names[i], s3_keys[i])
                local_path = os.path.join(cache_dir, f'{i}.jpg')
                with open(local_path, 'wb') as f:
                    f.write(img_bytes)
                local_paths.append(local_path)

            # --- Stratified validation split (20% per class) ---
            from collections import defaultdict
            class_indices = defaultdict(list)
            for i, l in enumerate(labels):
                class_indices[l].append(i)
            rng = np.random.default_rng(None)
            train_indices = []
            val_indices = []
            for cls, idxs in class_indices.items():
                idxs = rng.permutation(idxs).tolist()
                val_size = max(1, int(len(idxs) * 0.2))
                val_indices.extend(idxs[:val_size])
                train_indices.extend(idxs[val_size:])

            # Get the correct preprocessing function for the architecture
            preprocess_fn = None
            if hasattr(keras.applications, trained_model.architecture.lower()):
                arch_module = getattr(keras.applications, trained_model.architecture.lower(), None)
                if arch_module and hasattr(arch_module, 'preprocess_input'):
                    preprocess_fn = arch_module.preprocess_input
            if preprocess_fn is None:
                # Try common module names
                arch_modules = {
                    'MobileNetV2': keras.applications.mobilenet_v2,
                    'EfficientNetB0': keras.applications.efficientnet,
                    'EfficientNetB1': keras.applications.efficientnet,
                    'EfficientNetB2': keras.applications.efficientnet,
                    'ResNet50': keras.applications.resnet,
                    'VGG19': keras.applications.vgg19,
                    'InceptionV3': keras.applications.inception_v3,
                }
                module = arch_modules.get(trained_model.architecture)
                if module:
                    preprocess_fn = module.preprocess_input

            def load_local_image(path, label):
                img = tf.io.read_file(path)
                img = tf.image.decode_image(img, channels=3, expand_animations=False)
                img = tf.image.resize(img, [img_size, img_size])
                img = tf.cast(img, tf.float32)
                if preprocess_fn is not None:
                    img = preprocess_fn(img)
                else:
                    img = img / 255.0
                img = tf.ensure_shape(img, [img_size, img_size, 3])
                return img, label

            def make_dataset(idx_list):
                paths = [local_paths[i] for i in idx_list]
                lbls = [labels_onehot[i] for i in idx_list]
                ds = tf.data.Dataset.from_tensor_slices((paths, lbls))
                ds = ds.map(load_local_image, num_parallel_calls=tf.data.AUTOTUNE)
                return ds

            train_ds = make_dataset(train_indices).shuffle(len(train_indices)).batch(batch_size).prefetch(tf.data.AUTOTUNE)
            val_ds = make_dataset(val_indices).batch(batch_size).prefetch(tf.data.AUTOTUNE)

            # --- Build Keras model ---
            input_shape = (img_size, img_size, 3)

            if trained_model.architecture == 'custom':
                # Full custom architecture from layer dicts
                keras_model = keras.Sequential()
                for layer_def in trained_model.custom_architecture:
                    layer_type = layer_def.get('type')
                    layer_cls = getattr(keras.layers, layer_type, None)
                    if layer_cls is None:
                        return JsonResponse({'status': 'error', 'message': f'Unknown layer type "{layer_type}"'}, status=400)
                    params = {k: v for k, v in layer_def.items() if k != 'type'}
                    keras_model.add(layer_cls(**params))
            else:
                # Known Keras architecture
                arch_class = getattr(keras.applications, trained_model.architecture)
                base = arch_class(
                    weights='imagenet',
                    include_top=trained_model.include_top,
                    input_shape=input_shape if not trained_model.include_top else None,
                )

                if trained_model.include_top:
                    # Strip the original classification head and replace with num_classes
                    base.trainable = False
                    base_out = base.layers[-2].output  # second-to-last layer output
                    output = keras.layers.Dense(num_classes, activation='softmax')(base_out)
                    keras_model = keras.Model(inputs=base.input, outputs=output)
                else:
                    # Base without top + user-defined custom top layers
                    base.trainable = False
                    layers = [base]
                    if trained_model.custom_top_layers:
                        for layer_def in trained_model.custom_top_layers:
                            layer_type = layer_def.get('type')
                            layer_cls = getattr(keras.layers, layer_type, None)
                            if layer_cls is None:
                                return JsonResponse({'status': 'error', 'message': f'Unknown layer type "{layer_type}"'}, status=400)
                            params = {k: v for k, v in layer_def.items() if k != 'type'}
                            layers.append(layer_cls(**params))
                    else:
                        # Default top when none specified
                        layers.append(keras.layers.GlobalAveragePooling2D())
                        layers.append(keras.layers.Dense(num_classes, activation='softmax'))
                    keras_model = keras.Sequential(layers)

            keras_model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=lr),
                loss=trained_model.loss or 'sparse_categorical_crossentropy',
                metrics=trained_model.metrics or ['accuracy'],
            )

            # --- Compute class weights to handle imbalance ---
            from collections import Counter
            train_labels = [labels[i] for i in train_indices]
            label_counts = Counter(train_labels)
            total_train = len(train_labels)
            class_weight = {cls: total_train / (num_classes * count) for cls, count in label_counts.items()}

            # --- Train ---
            early_stop = keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=5, restore_best_weights=True
            )
            history = keras_model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=[early_stop], class_weight=class_weight)

            # --- Save weights and upload to S3 ---
            with tempfile.NamedTemporaryFile(suffix='.weights.h5', delete=False) as tmp:
                tmp_path = tmp.name
            try:
                keras_model.save_weights(tmp_path)
                file_size = os.path.getsize(tmp_path)
                with open(tmp_path, 'rb') as f:
                    model_bytes = f.read()
            finally:
                os.unlink(tmp_path)

            bucket_name = 'trained-models'
            s3_service.create_bucket(bucket_name)
            s3_key = f'trained-models/{trained_model.name}_v{(trained_model.current_version or 0) + 1}.weights.h5'
            metadata = s3_service.upload_file(bucket_name, s3_key, model_bytes)

            # --- Version the TrainedModel ---
            trained_model.current_version = (trained_model.current_version or 0) + 1
            trained_model.epochs = epochs
            trained_model.batch_size = batch_size
            trained_model.img_size = img_size
            trained_model.learning_rate = lr
            trained_model.create_version(
                path=metadata['path'],
                format='h5',
                size=file_size,
                notes=data.get('version_notes', f'Trained on project {project.name}'),
            )
            trained_model.save()

            # Clean up cache
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)

            final_metrics = {k: float(v[-1]) for k, v in history.history.items()}

            return JsonResponse({
                'status': 'success',
                'message': 'Model trained and saved',
                'trained_model': _serialize_trained_model(trained_model),
                'training': {
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'image_size': img_size,
                    'num_images': len(s3_keys),
                    'num_classes': num_classes,
                    'labels': unique_labels,
                    'final_metrics': final_metrics,
                    's3_path': metadata['path'],
                },
            }, status=200)
        except Exception as e:
            if 'cache_dir' in locals():
                import shutil
                shutil.rmtree(cache_dir, ignore_errors=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class InferenceView(View):
    def post(self, request):
        import tempfile
        import numpy as np
        from PIL import Image as PILImage
        from io import BytesIO

        try:
            project_id = request.POST.get('project_id')
            pretrained_model_id = request.POST.get('pretrained_model_id')
            image_file = request.FILES.get('image')

            if not project_id or not pretrained_model_id or not image_file:
                return JsonResponse({'status': 'error', 'message': 'project_id, pretrained_model_id, and image are required'}, status=400)

            # Validate project and model
            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

            pretrained_model = PreTrainedModel.objects(id=pretrained_model_id).first()
            if not pretrained_model:
                return JsonResponse({'status': 'error', 'message': 'PreTrainedModel not found'}, status=404)

            # Verify model is attached to project
            attached = any(
                str(ref._data.get('model_id', {}).id) == pretrained_model_id
                for ref in project.pretrained_models
                if ref._data.get('model_id') is not None
            )
            if not attached:
                return JsonResponse({'status': 'error', 'message': 'Model is not attached to this project'}, status=400)

            # Download model from S3
            s3_path = pretrained_model.path  # e.g. s3://pretrained-models/trained-models/VGG19_imagenet.weights.h5
            parts = s3_path.replace('s3://', '').split('/', 1)
            bucket_name, s3_key = parts[0], parts[1]

            s3_service = S3Service()
            model_bytes = s3_service.download_file(bucket_name, s3_key)

            # Load Keras model from bytes
            import tensorflow as tf
            with tempfile.NamedTemporaryFile(suffix='.weights.h5', delete=False) as tmp:
                tmp.write(model_bytes)
                tmp_path = tmp.name

            try:
                # Reconstruct architecture then load weights
                arch_name = pretrained_model.name.rsplit('_', 1)[0]
                available = [a for a in dir(tf.keras.applications) if not a.startswith('_')]
                arch_key = arch_name.lower().replace('-', '').replace('_', '')
                matched_arch = next(
                    (a for a in available if a.lower().replace('-', '').replace('_', '') == arch_key),
                    None,
                )
                if not matched_arch:
                    return JsonResponse({'status': 'error', 'message': f'Unknown architecture "{arch_name}"'}, status=400)

                arch_class = getattr(tf.keras.applications, matched_arch)
                keras_model = arch_class(weights=None, include_top=True)
                keras_model.load_weights(tmp_path)
            finally:
                os.unlink(tmp_path)

            # Determine expected input size from model
            input_shape = keras_model.input_shape  # e.g. (None, 224, 224, 3)
            target_h, target_w = input_shape[1], input_shape[2]

            # Load and resize image
            img = PILImage.open(BytesIO(image_file.read())).convert('RGB')
            img = img.resize((target_w, target_h))
            img_array = np.array(img, dtype='float32')
            img_array = np.expand_dims(img_array, axis=0)

            # Preprocess using the architecture-specific preprocessor
            preprocess_fn = None
            try:
                module = getattr(tf.keras.applications, matched_arch.lower(), None)
                if module is None:
                    for mod_name in dir(tf.keras.applications):
                        if mod_name.lower() == matched_arch.lower():
                            module = getattr(tf.keras.applications, mod_name)
                            break
                if module and hasattr(module, 'preprocess_input'):
                    preprocess_fn = module.preprocess_input
            except Exception:
                pass

            if preprocess_fn:
                img_array = preprocess_fn(img_array)

            # Run inference
            predictions = keras_model.predict(img_array)

            # Decode predictions (ImageNet top-N)
            num_classes = predictions.shape[-1]
            top_n = min(5, num_classes)
            decoded = tf.keras.applications.imagenet_utils.decode_predictions(predictions, top=top_n)[0]
            results = [{'class_id': class_id, 'label': label, 'confidence': round(float(score) * 100, 2)} for class_id, label, score in decoded]

            return JsonResponse({
                'status': 'success',
                'model_name': pretrained_model.name,
                'input_size': f'{target_w}x{target_h}',
                'predictions': results,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TrainedModelInferenceView(View):
    """
    POST /api/trained-models/inference/

    Run inference on a TrainedModel using its weights from S3.

    Form fields:
        - trained_model_id (required)
        - image (required, file upload)
        - version (optional, defaults to latest)
    """

    def post(self, request):
        import tempfile
        import numpy as np
        import tensorflow as tf
        import tensorflow.keras as keras
        from PIL import Image as PILImage
        from io import BytesIO

        try:
            trained_model_id = request.POST.get('trained_model_id')
            image_file = request.FILES.get('image')
            version_num = request.POST.get('version')

            if not trained_model_id or not image_file:
                return JsonResponse({'status': 'error', 'message': 'trained_model_id and image are required'}, status=400)

            trained_model = TrainedModel.objects(id=trained_model_id).first()
            if not trained_model:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)

            if not trained_model.versions:
                return JsonResponse({'status': 'error', 'message': 'TrainedModel has no trained versions'}, status=400)

            # Pick version
            if version_num:
                version = next((v for v in trained_model.versions if v.version == int(version_num)), None)
                if not version:
                    return JsonResponse({'status': 'error', 'message': f'Version {version_num} not found'}, status=404)
            else:
                version = trained_model.versions[-1]

            if not version.path:
                return JsonResponse({'status': 'error', 'message': 'Version has no S3 path'}, status=400)

            # Download weights from S3
            parts = version.path.replace('s3://', '').split('/', 1)
            bucket_name, s3_key = parts[0], parts[1]
            s3_service = S3Service()
            model_bytes = s3_service.download_file(bucket_name, s3_key)

            with tempfile.NamedTemporaryFile(suffix='.weights.h5', delete=False) as tmp:
                tmp.write(model_bytes)
                tmp_path = tmp.name

            try:
                # Use version's snapshot of architecture config
                arch = version.architecture or trained_model.architecture
                include_top = version.include_top if version.include_top is not None else trained_model.include_top
                custom_top = version.custom_top_layers or trained_model.custom_top_layers or []
                custom_arch = version.custom_architecture or trained_model.custom_architecture or []
                img_size = version.img_size or trained_model.img_size or 224

                num_classes = len(version.tags or trained_model.tags or [])
                input_shape = (img_size, img_size, 3)

                if arch == 'custom':
                    keras_model = keras.Sequential()
                    for layer_def in custom_arch:
                        layer_type = layer_def.get('type')
                        layer_cls = getattr(keras.layers, layer_type, None)
                        if layer_cls is None:
                            return JsonResponse({'status': 'error', 'message': f'Unknown layer type "{layer_type}"'}, status=400)
                        params = {k: v for k, v in layer_def.items() if k != 'type'}
                        keras_model.add(layer_cls(**params))
                else:
                    matched_arch = _resolve_keras_architecture(arch)
                    if not matched_arch:
                        return JsonResponse({'status': 'error', 'message': f'Unknown architecture "{arch}"'}, status=400)

                    arch_class = getattr(keras.applications, matched_arch)
                    base = arch_class(weights=None, include_top=include_top,
                                      input_shape=input_shape if not include_top else None)
                    base.trainable = False

                    if include_top:
                        base_out = base.layers[-2].output
                        output = keras.layers.Dense(num_classes, activation='softmax')(base_out)
                        keras_model = keras.Model(inputs=base.input, outputs=output)
                    else:
                        layers = [base]
                        if custom_top:
                            for layer_def in custom_top:
                                layer_type = layer_def.get('type')
                                layer_cls = getattr(keras.layers, layer_type, None)
                                if layer_cls is None:
                                    return JsonResponse({'status': 'error', 'message': f'Unknown layer type "{layer_type}"'}, status=400)
                                params = {k: v for k, v in layer_def.items() if k != 'type'}
                                layers.append(layer_cls(**params))
                        else:
                            layers.append(keras.layers.GlobalAveragePooling2D())
                            layers.append(keras.layers.Dense(num_classes, activation='softmax'))
                        keras_model = keras.Sequential(layers)

                # Build the model so weights can be loaded
                keras_model.build((None,) + input_shape)
                keras_model.load_weights(tmp_path)
            finally:
                os.unlink(tmp_path)

            # Preprocess image using architecture-specific preprocessing
            img = PILImage.open(BytesIO(image_file.read())).convert('RGB')
            img = img.resize((img_size, img_size))
            img_array = np.array(img, dtype='float32')
            img_array = np.expand_dims(img_array, axis=0)

            # Apply same preprocessing as training
            preprocess_fn = None
            arch_modules = {
                'MobileNetV2': tf.keras.applications.mobilenet_v2,
                'EfficientNetB0': tf.keras.applications.efficientnet,
                'EfficientNetB1': tf.keras.applications.efficientnet,
                'EfficientNetB2': tf.keras.applications.efficientnet,
                'ResNet50': tf.keras.applications.resnet,
                'VGG19': tf.keras.applications.vgg19,
                'InceptionV3': tf.keras.applications.inception_v3,
            }
            module = arch_modules.get(arch)
            if module:
                preprocess_fn = module.preprocess_input
            if preprocess_fn:
                img_array = preprocess_fn(img_array)
            else:
                img_array = img_array / 255.0

            # Run inference
            predictions = keras_model.predict(img_array)

            # Map predictions to tag labels
            tags = version.tags or trained_model.tags or []
            tag_names = sorted(set(ref.name for ref in tags))
            results = []
            for i, score in enumerate(predictions[0]):
                label = tag_names[i] if i < len(tag_names) else f'class_{i}'
                results.append({'label': label, 'confidence': round(float(score) * 100, 2)})
            results.sort(key=lambda x: x['confidence'], reverse=True)

            return JsonResponse({
                'status': 'success',
                'model_name': trained_model.name,
                'version': version.version,
                'input_size': f'{img_size}x{img_size}',
                'predictions': results,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ImageView(View):
    BUCKET_NAME = 'images'

    def _serialize(self, img):
        return {
            'id': str(img.id),
            'path': img.path,
            'bucket_name': img.bucket_name,
            'key': img.key,
            'size': img.size,
            'format': img.format,
            'content_type': img.content_type,
            'etag': img.etag,
            'last_modified': img.last_modified.isoformat() if img.last_modified else None,
            'project_id': str(img.project.id) if img.project else None,
            'tag_references': serialize_tag_references(img.tag_references),
        }

    # GET - List all images or get specific image
    def get(self, request, image_id=None):
        try:
            if image_id:
                img = Image.objects(id=image_id).first()
                if not img:
                    return JsonResponse({'status': 'error', 'message': 'Image not found'}, status=404)
                return JsonResponse({'status': 'success', 'image': self._serialize(img)})
            else:
                images = Image.objects.all()
                image_list = [self._serialize(img) for img in images]
                return JsonResponse({'status': 'success', 'images': image_list, 'count': len(image_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST - Upload image(s) to S3 and create Image document(s). Accepts a single image or a zip file.
    def post(self, request):
        try:
            user_id = request.POST.get('user_id')
            project_id = request.POST.get('project_id')
            file = request.FILES.get('file')

            if not file:
                return JsonResponse({'status': 'error', 'message': 'file is required'}, status=400)
            if not user_id:
                return JsonResponse({'status': 'error', 'message': 'user_id is required'}, status=400)
            if not project_id:
                return JsonResponse({'status': 'error', 'message': 'project_id is required'}, status=400)

            user = User.objects(id=user_id).first()
            if not user:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)

            project = Project.objects(id=project_id).first()
            if not project:
                return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

            # Resolve optional tag references
            tags_data = request.POST.get('tags')
            tag_refs = []
            if tags_data:
                tag_refs = resolve_tag_references(json.loads(tags_data), project)

            s3_service = S3Service()
            s3_service.create_bucket(self.BUCKET_NAME)

            IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')

            # Check if the uploaded file is a zip
            if file.name.lower().endswith('.zip'):
                file_bytes = file.read()
                if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
                    return JsonResponse({'status': 'error', 'message': 'Invalid zip file'}, status=400)

                images = []
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    for entry in zf.namelist():
                        # Skip directories and non-image files
                        if entry.endswith('/') or not entry.lower().endswith(IMAGE_EXTENSIONS):
                            continue
                        filename = os.path.basename(entry)
                        if not filename:
                            continue
                        img_data = zf.read(entry)
                        s3_key = f'{user_id}/{project_id}/{filename}'
                        metadata = s3_service.upload_file(self.BUCKET_NAME, s3_key, img_data)

                        img = Image(
                            path=metadata['path'],
                            bucket_name=self.BUCKET_NAME,
                            key=s3_key,
                            size=metadata.get('size'),
                            format=filename.rsplit('.', 1)[-1] if '.' in filename else None,
                            content_type=metadata.get('content_type'),
                            etag=metadata.get('etag'),
                            last_modified=metadata.get('last_modified'),
                            project=project,
                            tag_references=tag_refs,
                        )
                        img.save()
                        images.append(img)

                if not images:
                    return JsonResponse({'status': 'error', 'message': 'No valid images found in zip file'}, status=400)

                return JsonResponse({
                    'status': 'success',
                    'message': f'{len(images)} images uploaded and created',
                    'images': [self._serialize(img) for img in images],
                }, status=201)

            # Single image upload
            s3_key = f'{user_id}/{project_id}/{file.name}'
            metadata = s3_service.upload_file(self.BUCKET_NAME, s3_key, file.read())

            img = Image(
                path=metadata['path'],
                bucket_name=self.BUCKET_NAME,
                key=s3_key,
                size=metadata.get('size'),
                format=file.name.rsplit('.', 1)[-1] if '.' in file.name else None,
                content_type=metadata.get('content_type'),
                etag=metadata.get('etag'),
                last_modified=metadata.get('last_modified'),
                project=project,
                tag_references=tag_refs,
            )
            img.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Image uploaded and created',
                'image': self._serialize(img),
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # PUT - Update image metadata
    def put(self, request, image_id):
        try:
            img = Image.objects(id=image_id).first()
            if not img:
                return JsonResponse({'status': 'error', 'message': 'Image not found'}, status=404)

            data = json.loads(request.body)

            
            if 'tags' in data:
                img.tag_references = resolve_tag_references(data['tags'], img.project)

            img.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Image updated',
                'image': self._serialize(img),
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # DELETE - Delete image
    def delete(self, request, image_id):
        try:
            img = Image.objects(id=image_id).first()
            if not img:
                return JsonResponse({'status': 'error', 'message': 'Image not found'}, status=404)

            img.delete()
            return JsonResponse({'status': 'success', 'message': 'Image deleted'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
