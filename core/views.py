import os

# Must be set before TensorFlow is imported anywhere (suppresses GPU/TRT library warnings on CPU-only machines)
#os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
#os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
#os.environ.setdefault('TF_TRT_LOGGER_VERBOSITY', '0')
#os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')

from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .services import S3Service
from .models import User, Project, Image, Tag, TagReference, TrainedModel, TrainedModelReference, PreTrainedModel, PreTrainedModelReference
import json
from bson import ObjectId
from functools import wraps


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
      - {"name": "<str>", "path": "<str>"}               → look up TrainedModel by name; create if missing
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
                path = item.get('path', '')
                model = TrainedModel(name=name, description=description, path=path)
                model.save()
        else:
            model = TrainedModel.objects(name=name).first()
            if not model:
                path = item.get('path', '')
                model = TrainedModel(name=name, description=description, path=path)
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
            def serialize_project(project):
                return {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'tags': serialize_tag_references(project.tags),
                    'trained_models': serialize_trained_model_references(project.trained_models),
                    'pretrained_models': serialize_pretrained_model_references(project.pretrained_models),
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
                project.tags = resolve_tag_references(scoped)
                project.save()

            print("asdsadass")
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
                project.tags = resolve_tag_references(data['tags'])
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
            bucket_name = data.get('bucket_name', 'pretrained-models')
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

                # --- Save model to a temp .h5 file and read bytes ---
                with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    keras_model.save(tmp_path)
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

                s3_key = f'trained-models/{model_name}.h5'

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


@method_decorator(csrf_exempt, name='dispatch')
class TrainedModelView(View):
    # GET - List all trained models or get specific model
    def get(self, request, model_id=None):
        try:
            if model_id:
                model = TrainedModel.objects(id=model_id).first()
                if not model:
                    return JsonResponse({'status': 'error', 'message': 'TrainedModel not found'}, status=404)

                return JsonResponse({
                    'status': 'success',
                    'trained_model': {
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
                models = TrainedModel.objects.all()
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

                return JsonResponse({'status': 'success', 'trained_models': model_list, 'count': len(model_list)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST - Create trained model
    def post(self, request):
        try:
            data = json.loads(request.body)

            name = data.get('name')
            path = data.get('path')

            if not name:
                return JsonResponse({'status': 'error', 'message': 'name is required'}, status=400)
            if not path:
                return JsonResponse({'status': 'error', 'message': 'path is required'}, status=400)

            model = TrainedModel(
                name=name,
                description=data.get('description', ''),
                path=path,
                format=data.get('format'),
                size=data.get('size'),
            )
            model.save()

            return JsonResponse({
                'status': 'success',
                'message': 'TrainedModel created',
                'trained_model': {
                    'id': str(model.id),
                    'name': model.name,
                    'description': model.description,
                    'path': model.path,
                    'format': model.format,
                    'size': model.size,
                }
            }, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # PUT - Update trained model
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
            if 'path' in data:
                model.path = data['path']
            if 'format' in data:
                model.format = data['format']
            if 'size' in data:
                model.size = data['size']

            model.save()

            return JsonResponse({
                'status': 'success',
                'message': 'TrainedModel updated',
                'trained_model': {
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
            
            # Create tag references from provided tag_ids
            tag_references = []
            for tag_id in tag_ids:
                tag = Tag.objects(id=tag_id).first()
                if tag:
                    tag_references.append(TagReference(tag_id=tag, name=tag.name))
            
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
