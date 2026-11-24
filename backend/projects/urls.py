from django.urls import path
from projects.views import (
    ClientListCreateView,
    ClientDetailView,
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListCreateView,
    ProjectMemberDetailView,
)

app_name = 'projects'

urlpatterns = [
    # Clients
    path('<uuid:workspace_id>/clients/', ClientListCreateView.as_view(), name='client-list-create'),
    path('<uuid:workspace_id>/clients/<uuid:id>/', ClientDetailView.as_view(), name='client-detail'),

    # Projects
    path('<uuid:workspace_id>/projects/', ProjectListCreateView.as_view(), name='project-list-create'),
    path('<uuid:workspace_id>/projects/<uuid:id>/', ProjectDetailView.as_view(), name='project-detail'),

    # Project Members
    path('<uuid:workspace_id>/projects/<uuid:project_id>/members/', ProjectMemberListCreateView.as_view(), name='project-member-list-create'),
    path('<uuid:workspace_id>/projects/<uuid:project_id>/members/<uuid:id>/', ProjectMemberDetailView.as_view(), name='project-member-detail'),
]
