from django.urls import path
from .views import HomeView, S3View, AuthView, UserView, ProjectView, TagView, LoginPageView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginPageView.as_view(), name='login'),
    path('s3/', S3View.as_view(), name='s3'),
    
    # Authentication endpoints
    path('api/auth/', AuthView.as_view(), name='auth'),
    
    # User CRUD endpoints
    path('api/users/', UserView.as_view(), name='user-list-create'),
    path('api/users/<str:user_id>/', UserView.as_view(), name='user-detail'),
    
    # Project CRUD endpoints
    path('api/projects/', ProjectView.as_view(), name='project-list-create'),
    path('api/projects/<str:project_id>/', ProjectView.as_view(), name='project-detail'),
    
    # Tag CRUD endpoints
    path('api/tags/', TagView.as_view(), name='tag-list-create'),
    path('api/tags/<str:tag_id>/', TagView.as_view(), name='tag-detail'),
]
