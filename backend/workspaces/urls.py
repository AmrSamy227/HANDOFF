from django.urls import path
from workspaces.views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    TransferOwnershipView,
    WorkspaceMemberListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceInvitationListCreateView,
    WorkspaceInvitationRevokeView,
    AcceptInvitationView,
)

app_name = 'workspaces'

urlpatterns = [
    path('', WorkspaceListCreateView.as_view(), name='workspace-list-create'),
    path('<uuid:id>/', WorkspaceDetailView.as_view(), name='workspace-detail'),
    path('<uuid:id>/transfer-ownership/', TransferOwnershipView.as_view(), name='workspace-transfer-ownership'),
    path('<uuid:workspace_id>/members/', WorkspaceMemberListCreateView.as_view(), name='workspace-member-list'),
    path('<uuid:workspace_id>/members/<uuid:id>/', WorkspaceMemberDetailView.as_view(), name='workspace-member-detail'),
    path('<uuid:workspace_id>/invitations/', WorkspaceInvitationListCreateView.as_view(), name='workspace-invitation-list-create'),
    path('<uuid:workspace_id>/invitations/<uuid:id>/revoke/', WorkspaceInvitationRevokeView.as_view(), name='workspace-invitation-revoke'),
]
