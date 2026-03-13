from django.urls import path
from .views import HomeView, InferenceView, AuthView, UserView, ProjectView, TagView, LoginPageView, TrainedModelView, PreTrainedModelView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginPageView.as_view(), name='login'),
    path('api/inference/', InferenceView.as_view(), name='inference'),
    
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

    # TrainedModel CRUD endpoints
    path('api/trained-models/', TrainedModelView.as_view(), name='trained-model-list-create'),
    path('api/trained-models/<str:model_id>/', TrainedModelView.as_view(), name='trained-model-detail'),

    # PreTrainedModel CRUD endpoints
    path('api/pretrained-models/', PreTrainedModelView.as_view(), name='pretrained-model-list-create'),
    path('api/pretrained-models/<str:model_id>/', PreTrainedModelView.as_view(), name='pretrained-model-detail'),
]
