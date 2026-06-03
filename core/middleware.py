import jwt
from django.conf import settings
from django.http import JsonResponse


class JWTAuthMiddleware:
    EXEMPT_PATHS = ['/api/auth/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/') or request.path in self.EXEMPT_PATHS:
            return self.get_response(request)

        auth_header = request.headers.get('Authorization', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        elif '/file/' in request.path and request.GET.get('token'):
            token = request.GET.get('token')

        if not token:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return JsonResponse({'status': 'error', 'message': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'status': 'error', 'message': 'Invalid token'}, status=401)

        return self.get_response(request)
