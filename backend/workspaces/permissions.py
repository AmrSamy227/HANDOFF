from rest_framework import permissions
from workspaces.models import WorkspaceMember


def get_active_membership(user, workspace):
    """Returns active WorkspaceMember instance if exists, otherwise None."""
    if not user or not user.is_authenticated or not workspace:
        return None
    return WorkspaceMember.objects.filter(
        workspace=workspace,
        user=user,
        status='active'
    ).select_related('workspace', 'client').first()


class IsWorkspaceOwner(permissions.BasePermission):
    """Allows access only to active owners of the workspace."""

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership
        return membership.role == 'owner'


class IsWorkspaceAdmin(permissions.BasePermission):
    """Allows access to active owners and admins of the workspace."""

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership
        return membership.role in ('owner', 'admin')


class IsWorkspaceMember(permissions.BasePermission):
    """Allows access to any active member of the workspace (owner, admin, member, client)."""

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership
        return True


class IsNotClientRole(permissions.BasePermission):
    """Allows access only to internal workspace roles (owner, admin, member)."""

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership
        return membership.role != 'client'
