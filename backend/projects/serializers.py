from rest_framework import serializers
from django.contrib.auth import get_user_model
from projects.models import Client, Project, ProjectMember
from workspaces.models import WorkspaceMember
from workspaces.serializers import WorkspaceMemberUserSerializer

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id',
            'workspace',
            'name',
            'contact_email',
            'contact_phone',
            'company_website',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'workspace', 'created_at', 'updated_at']

    def validate_name(self, value):
        workspace = self.context.get('workspace')
        instance = getattr(self, 'instance', None)
        qs = Client.objects.filter(workspace=workspace, name__iexact=value.strip())
        if instance:
            qs = qs.exclude(id=instance.id)
        if qs.exists():
            raise serializers.ValidationError("A client organization with this name already exists in this workspace.")
        return value.strip()


class ProjectSerializer(serializers.ModelSerializer):
    created_by = WorkspaceMemberUserSerializer(read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'id',
            'workspace',
            'client',
            'client_name',
            'name',
            'description',
            'status',
            'start_date',
            'deadline',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'workspace', 'client_name', 'created_by', 'created_at', 'updated_at']

    def validate_name(self, value):
        workspace = self.context.get('workspace')
        instance = getattr(self, 'instance', None)
        qs = Project.objects.filter(workspace=workspace, name__iexact=value.strip())
        if instance:
            qs = qs.exclude(id=instance.id)
        if qs.exists():
            raise serializers.ValidationError("A project with this name already exists in this workspace.")
        return value.strip()

    def validate_client(self, value):
        workspace = self.context.get('workspace')
        if value and workspace and value.workspace_id != workspace.id:
            raise serializers.ValidationError("Client must belong to the same workspace.")
        return value


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = WorkspaceMemberUserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            'id',
            'project',
            'user',
            'user_id',
            'role',
            'created_at',
        ]
        read_only_fields = ['id', 'project', 'created_at']

    def validate(self, attrs):
        project = self.context['project']
        workspace = project.workspace
        instance = getattr(self, 'instance', None)
        role = attrs.get('role', instance.role if instance else 'collaborator')
        user_id = attrs.get('user_id', instance.user_id if instance else None)

        if not user_id:
            raise serializers.ValidationError({"user_id": "User ID is required."})

        # Verify target user is an active WorkspaceMember of the project's workspace
        ws_member = WorkspaceMember.objects.filter(
            workspace=workspace,
            user_id=user_id,
            status='active'
        ).first()

        if not ws_member:
            raise serializers.ValidationError({"user_id": "User must be an active member of this workspace to join the project."})

        # Unique user per project
        if not instance:
            if ProjectMember.objects.filter(project=project, user_id=user_id).exists():
                raise serializers.ValidationError({"user_id": "User is already assigned to this project."})

        # Eligibility checks based on workspace role
        if ws_member.role == 'client':
            # Client workspace members can only join projects assigned to their client organization
            if not project.client_id or project.client_id != ws_member.client_id:
                raise serializers.ValidationError({
                    "user_id": "Client workspace members can only be assigned to projects belonging to their organization."
                })
            # Client members can only have 'client' role on project
            if role != 'client':
                raise serializers.ValidationError({
                    "role": "Client workspace members must be assigned the 'client' role on projects."
                })
        else:
            # Internal workspace members cannot have 'client' role on project
            if role == 'client':
                raise serializers.ValidationError({
                    "role": "Internal workspace members cannot have the 'client' reviewer role on projects."
                })

        attrs['user_obj'] = ws_member.user
        return attrs

    def create(self, validated_data):
        project = self.context['project']
        user = validated_data.pop('user_obj')
        validated_data.pop('user_id')
        return ProjectMember.objects.create(
            project=project,
            user=user,
            **validated_data
        )
