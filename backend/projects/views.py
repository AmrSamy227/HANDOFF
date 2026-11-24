from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from workspaces.views import WorkspaceScopedMixin
from workspaces.permissions import IsWorkspaceAdmin, IsNotClientRole
from workspaces.models import Workspace
from projects.models import Client, Project, ProjectMember
from projects.serializers import ClientSerializer, ProjectSerializer, ProjectMemberSerializer
from projects.permissions import CanManageProjects, CanManageProjectMembers


class ClientListCreateView(WorkspaceScopedMixin, generics.ListCreateAPIView):
    """
    GET: List clients in workspace (Internal members only).
    POST: Create client in workspace (Internal members only).
    """
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsNotClientRole]

    def get_queryset(self):
        return Client.objects.filter(workspace=self.workspace).order_by('name')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def perform_create(self, serializer):
        serializer.save(workspace=self.workspace)


class ClientDetailView(WorkspaceScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Client detail (Internal members only).
    PATCH: Update client (Internal members only).
    DELETE: Delete client (Admin/Owner only).
    """
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsNotClientRole]
    lookup_field = 'id'

    def get_queryset(self):
        return Client.objects.filter(workspace=self.workspace)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'DELETE':
            if self.workspace_member.role not in ('owner', 'admin'):
                raise PermissionDenied("Only workspace owners and admins can delete client organizations.")

    def perform_destroy(self, instance):
        from django.db.models import ProtectedError
        from rest_framework.exceptions import ValidationError
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete client organization with associated workspace members."})


class ProjectListCreateView(WorkspaceScopedMixin, generics.ListCreateAPIView):
    """
    GET: List projects in workspace.
         - Internal members see all projects in the workspace.
         - Client members see ONLY projects linked to their client organization WHERE they are assigned as ProjectMember.
    POST: Create project in workspace (Internal members only).
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, CanManageProjects]

    def get_queryset(self):
        base_qs = Project.objects.filter(workspace=self.workspace).select_related('client', 'created_by')
        if self.workspace_member.role in ('owner', 'admin', 'member'):
            return base_qs.order_by('-created_at')
        elif self.workspace_member.role == 'client':
            if not self.workspace_member.client:
                return Project.objects.none()
            return base_qs.filter(
                client=self.workspace_member.client,
                project_members__user=self.request.user
            ).distinct().order_by('-created_at')
        return Project.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def perform_create(self, serializer):
        serializer.save(workspace=self.workspace, created_by=self.request.user)


class ProjectDetailView(WorkspaceScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Project detail (respects client tenant isolation; returns 404 if inaccessible).
    PATCH: Update project (Internal members only).
    DELETE: Delete project (Admin/Owner or creator only).
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, CanManageProjects]
    lookup_field = 'id'

    def get_queryset(self):
        base_qs = Project.objects.filter(workspace=self.workspace).select_related('client', 'created_by')
        if self.workspace_member.role in ('owner', 'admin', 'member'):
            return base_qs
        elif self.workspace_member.role == 'client':
            if not self.workspace_member.client:
                return Project.objects.none()
            return base_qs.filter(
                client=self.workspace_member.client,
                project_members__user=self.request.user
            ).distinct()
        return Project.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.workspace
        return context

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method == 'DELETE':
            project = self.get_object()
            if self.workspace_member.role not in ('owner', 'admin') and project.created_by_id != request.user.id:
                raise PermissionDenied("Only workspace admins or the project creator can delete this project.")


class ProjectScopedMixin(WorkspaceScopedMixin):
    """
    Resolves project from URL within workspace context and verifies caller has project access.
    Returns 404 for non-existent or inaccessible projects (IDOR protection).
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
            from workspaces.permissions import get_active_membership
            membership = get_active_membership(request.user, self.workspace)
            if not membership:
                raise Http404("Workspace not found.")
            self.workspace_member = membership
            request.workspace_member = membership

        project_id = kwargs.get('project_id')
        if not project_id:
            raise Http404("Project not found.")

        base_qs = Project.objects.filter(workspace=self.workspace, id=project_id)
        if hasattr(self, 'workspace_member') and self.workspace_member.role == 'client':
            if not self.workspace_member.client:
                raise Http404("Project not found.")
            base_qs = base_qs.filter(
                client=self.workspace_member.client,
                project_members__user=request.user
            )

        try:
            project = base_qs.first()
        except ValueError:
            raise Http404("Project not found.")

        if not project:
            raise Http404("Project not found.")

        self.project = project

        super(WorkspaceScopedMixin, self).initial(request, *args, **kwargs)


class ProjectMemberListCreateView(ProjectScopedMixin, generics.ListCreateAPIView):
    """
    GET: List project members.
    POST: Assign user to project (Lead, Admin, or Owner only).
    """
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated, CanManageProjectMembers]

    def get_queryset(self):
        return ProjectMember.objects.filter(project=self.project).select_related('user').order_by('created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.project
        return context


class ProjectMemberDetailView(ProjectScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Project member detail.
    PATCH: Update project member role.
    DELETE: Remove user from project.
    """
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated, CanManageProjectMembers]
    lookup_field = 'id'

    def get_queryset(self):
        return ProjectMember.objects.filter(project=self.project)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.project
        return context
