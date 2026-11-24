from rest_framework import permissions
from workspaces.permissions import get_active_membership


class CanManageProjects(permissions.BasePermission):
    """
    Only internal workspace members (owner, admin, member) can create, update, or delete projects.
    Clients have read-only access (GET/HEAD/OPTIONS).
    """

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership

        # Read permissions are allowed to any workspace member (subject to queryset filtering)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions (POST, PUT, PATCH, DELETE) require internal workspace role
        return membership.role in ('owner', 'admin', 'member')


class CanManageProjectMembers(permissions.BasePermission):
    """
    Project members can be managed by:
    - Workspace owner or admin
    - Project lead (lead role on this project)
    Clients and collaborators cannot add/remove project members.
    """

    def has_permission(self, request, view):
        workspace = getattr(view, 'workspace', None)
        if not workspace:
            return False
        membership = get_active_membership(request.user, workspace)
        if not membership:
            return False
        request.workspace_member = membership

        if request.method in permissions.SAFE_METHODS:
            return True

        # Owner/admin can always manage project members
        if membership.role in ('owner', 'admin'):
            return True

        # Project lead check
        project = getattr(view, 'project', None)
        if project and project.project_members.filter(user=request.user, role='lead').exists():
            return True

        return False
