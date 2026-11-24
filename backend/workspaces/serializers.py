from rest_framework import serializers
from django.contrib.auth import get_user_model
from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspaces.services import create_workspace, create_invitation, transfer_ownership
from projects.models import Client

User = get_user_model()


class WorkspaceMemberUserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar']
        read_only_fields = fields


class WorkspaceClientMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name']
        read_only_fields = fields


class WorkspaceSerializer(serializers.ModelSerializer):
    owner = WorkspaceMemberUserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id',
            'name',
            'slug',
            'workspace_type',
            'owner',
            'logo',
            'member_count',
            'user_role',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'owner', 'member_count', 'user_role', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(status='active').count()

    def get_user_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user, status='active').first()
        return membership.role if membership else None

    def create(self, validated_data):
        user = self.context['request'].user
        name = validated_data.get('name')
        workspace_type = validated_data.get('workspace_type', 'personal')
        logo = validated_data.get('logo', None)
        return create_workspace(user=user, name=name, workspace_type=workspace_type, logo=logo)


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = WorkspaceMemberUserSerializer(read_only=True)
    client_detail = WorkspaceClientMinimalSerializer(source='client', read_only=True)
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = WorkspaceMember
        fields = [
            'id',
            'workspace',
            'user',
            'role',
            'status',
            'client',
            'client_detail',
            'joined_at',
        ]
        read_only_fields = ['id', 'workspace', 'user', 'client_detail', 'joined_at']

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        role = attrs.get('role', instance.role if instance else 'member')
        status = attrs.get('status', instance.status if instance else 'active')
        client = attrs.get('client', instance.client if instance else None)
        workspace = instance.workspace if instance else self.context.get('workspace')

        # Owner protection: cannot modify role or status of owner directly
        if instance and instance.role == 'owner':
            if 'role' in attrs and attrs['role'] != 'owner':
                raise serializers.ValidationError({"role": "Cannot change the role of the workspace owner. Use transfer-ownership instead."})
            if 'status' in attrs and attrs['status'] != 'active':
                raise serializers.ValidationError({"status": "Cannot suspend the workspace owner."})

        # Cannot assign owner role directly
        if role == 'owner' and (not instance or instance.role != 'owner'):
            raise serializers.ValidationError({"role": "Owner role cannot be assigned directly. Use transfer-ownership instead."})

        # Role-client consistency
        if role == 'client':
            if not client:
                raise serializers.ValidationError({"client": "Client organization is required for client role members."})
            if workspace and client.workspace_id != workspace.id:
                raise serializers.ValidationError({"client": "Client organization must belong to this workspace."})
        else:
            if client is not None:
                raise serializers.ValidationError({"client": "Internal roles (admin, member) cannot be linked to a client organization."})

        return attrs


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    invited_by = WorkspaceMemberUserSerializer(read_only=True)
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True
    )
    raw_token = serializers.CharField(read_only=True)

    class Meta:
        model = WorkspaceInvitation
        fields = [
            'id',
            'workspace',
            'email',
            'role',
            'client',
            'invited_by',
            'status',
            'raw_token',
            'expires_at',
            'created_at',
            'accepted_at',
        ]
        read_only_fields = [
            'id',
            'workspace',
            'invited_by',
            'status',
            'raw_token',
            'expires_at',
            'created_at',
            'accepted_at',
        ]

    def validate_role(self, value):
        if value not in dict(WorkspaceInvitation.INVITABLE_ROLES):
            raise serializers.ValidationError(f"Role '{value}' cannot be invited. Owner role must be transferred.")
        return value

    def validate(self, attrs):
        workspace = self.context['workspace']
        email = attrs.get('email', '').strip().lower()
        role = attrs.get('role', 'member')
        client = attrs.get('client', None)

        if not email:
            raise serializers.ValidationError({"email": "Email is required."})

        # Role-client consistency
        if role == 'client':
            if not client:
                raise serializers.ValidationError({"client": "Client organization is required for client role invitations."})
            if client.workspace_id != workspace.id:
                raise serializers.ValidationError({"client": "Client organization must belong to this workspace."})
        else:
            if client is not None:
                raise serializers.ValidationError({"client": "Internal roles cannot be linked to a client organization."})

        # Check existing active membership
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user and WorkspaceMember.objects.filter(workspace=workspace, user=existing_user, status='active').exists():
            raise serializers.ValidationError({"email": "User with this email is already an active member of this workspace."})

        # Check existing pending invite
        if WorkspaceInvitation.objects.filter(workspace=workspace, email__iexact=email, status='pending').exists():
            raise serializers.ValidationError({"email": "An active pending invitation for this email already exists in this workspace."})

        return attrs

    def create(self, validated_data):
        workspace = self.context['workspace']
        inviter = self.context['request'].user
        email = validated_data['email']
        role = validated_data['role']
        client = validated_data.get('client', None)

        invitation, raw_token = create_invitation(
            workspace=workspace,
            inviter=inviter,
            email=email,
            role=role,
            client=client
        )
        invitation.raw_token = raw_token
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, write_only=True)


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_id = serializers.UUIDField(required=True)
