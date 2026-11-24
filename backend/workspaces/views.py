import uuid
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspaces.serializers import (
    WorkspaceSerializer,
    WorkspaceMemberSerializer,
    WorkspaceInvitationSerializer,
    AcceptInvitationSerializer,
    TransferOwnershipSerializer,
)
from workspaces.services import accept_invitation, revoke_invitation, transfer_ownership
from workspaces.permissions import (
    IsWorkspaceOwner,
    IsWorkspaceAdmin,
    IsWorkspaceMember,
    get_active_membership,
)


class WorkspaceListCreateView(generics.ListCreateAPIView):
    """
    GET: List all workspaces where the current user has an active membership.
    POST: Create a new workspace and automatically establish the user as the Owner member.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(
            memberships__user=self.request.user,
            memberships__status='active'
        ).distinct()


class WorkspaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve workspace details if user is an active member (404 otherwise).
    PATCH: Update workspace (Name, logo, type) - Admin/Owner only.
    DELETE: Delete workspace - Owner only.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Only return workspaces user belongs to
        return Workspace.objects.filter(
            memberships__user=self.request.user,
            memberships__status='active'
        ).distinct()

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ['PUT', 'PATCH']:
            workspace = self.get_object()
            membership = get_active_membership(request.user, workspace)
            if not membership or membership.role not in ('owner', 'admin'):
                self.permission_denied(request, message="Only workspace owners and admins can update the workspace.")
        elif request.method == 'DELETE':
            workspace = self.get_object()
            membership = get_active_membership(request.user, workspace)
            if not membership or membership.role != 'owner':
                self.permission_denied(request, message="Only the workspace owner can delete the workspace.")


class TransferOwnershipView(APIView):
    """
    POST: Transfer workspace ownership to an active member. Requires current owner.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            workspace = Workspace.objects.get(id=id)
        except (Workspace.DoesNotExist, ValueError):
            raise Http404("Workspace not found.")

        membership = get_active_membership(request.user, workspace)
        if not membership or membership.role != 'owner':
            raise Http404("Workspace not found.")

        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_owner_id = serializer.validated_data['new_owner_id']
        updated_ws = transfer_ownership(
            workspace=workspace,
            current_owner=request.user,
            new_owner_id=new_owner_id
        )
        return Response(WorkspaceSerializer(updated_ws, context={'request': request}).data, status=status.HTTP_200_OK)


class WorkspaceScopedMixin:
    """
    Enforces that request.user is an active member of the workspace specified in the URL.
    Returns 404 for unauthenticated or non-member requests to prevent IDOR / leaking resource existence.
    """
    def initial(self, request, *args, **kwargs):
        workspace_id = kwargs.get('workspace_id')
        if not workspace_id:
            raise Http404("Workspace not found.")

        try:
            self.workspace = Workspace.objects.get(id=workspace_id)
        except (Workspace.DoesNotExist, ValueError):
            raise Http404("Workspace not found.")

        self.perform_authentication(request)

        if request.user and request.user.is_authenticated:
            membership = get_active_membership(request.user, self.workspace)
            if not membership:
                raise Http404("Workspace not found.")
            self.workspace_member = membership
            request.workspace_member = membership

        super().initial(request, *args, **kwargs)


class WorkspaceMemberListCreateView(WorkspaceScopedMixin, generics.ListAPIView):
    """
    GET: List active and suspended members of this workspace.
    """
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        return WorkspaceMember.objects.filter(
            workspace=self.workspace
        ).select_related('user', 'client').order_by('joined_at')


class WorkspaceMemberDetailView(WorkspaceScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Member detail.
    PATCH: Update role / status. Admin/Owner only. Cannot modify Owner directly.
    DELETE: Remove member. Admin/Owner only. Cannot delete Owner.
    """
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    lookup_field = 'id'

    def get_queryset(self):
        return WorkspaceMember.objects.filter(workspace=self.workspace)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def perform_destroy(self, instance):
        if instance.role == 'owner':
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "Cannot remove the workspace owner."})
        instance.delete()


class WorkspaceInvitationListCreateView(WorkspaceScopedMixin, generics.ListCreateAPIView):
    """
    GET: List pending invitations for the workspace. Admin/Owner only.
    POST: Create a new invitation (returns raw token in response). Admin/Owner only.
    """
    serializer_class = WorkspaceInvitationSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def get_queryset(self):
        return WorkspaceInvitation.objects.filter(
            workspace=self.workspace
        ).select_related('invited_by', 'client').order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        response_data = serializer.data
        response_data['raw_token'] = invitation.raw_token
        return Response(response_data, status=status.HTTP_201_CREATED)


class WorkspaceInvitationRevokeView(WorkspaceScopedMixin, APIView):
    """
    POST: Revoke a pending invitation. Admin/Owner only.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request, workspace_id, id):
        invitation = revoke_invitation(
            workspace=self.workspace,
            invitation_id=id,
            user=request.user
        )
        return Response(
            WorkspaceInvitationSerializer(invitation, context={'workspace': self.workspace}).data,
            status=status.HTTP_200_OK
        )


class AcceptInvitationView(APIView):
    """
    POST: Accept a workspace invitation using raw token.
    Enforces identity matching, expiration, and replay protection.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        membership = accept_invitation(raw_token=token, user=request.user)
        return Response(
            WorkspaceMemberSerializer(membership).data,
            status=status.HTTP_200_OK
        )
