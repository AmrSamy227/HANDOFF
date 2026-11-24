import hashlib
import secrets
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation

User = get_user_model()


def hash_token(raw_token: str) -> str:
    """Generate SHA-256 hash for secure token storage."""
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def create_workspace(
    user,
    name: str,
    workspace_type: str = 'personal',
    logo=None
) -> Workspace:
    """
    Atomically creates a workspace and assigns the creator as the Owner member.
    """
    with transaction.atomic():
        workspace = Workspace.objects.create(
            name=name,
            workspace_type=workspace_type,
            owner=user,
            logo=logo
        )
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role='owner',
            status='active',
            client=None
        )
        return workspace


def create_invitation(
    workspace: Workspace,
    inviter,
    email: str,
    role: str,
    client=None,
    expires_in_days: int = 7
) -> tuple[WorkspaceInvitation, str]:
    """
    Creates a secure workspace invitation using secrets.token_urlsafe(32) and SHA-256 hashing.
    Enforces invitable roles, role-client consistency, and duplicate checks.
    """
    if role not in dict(WorkspaceInvitation.INVITABLE_ROLES):
        raise ValidationError({"role": f"Role '{role}' cannot be invited. Owner role must be transferred."})

    # Role-client consistency
    if role == 'client':
        if not client:
            raise ValidationError({"client": "Client organization is required for client role invitations."})
        if client.workspace_id != workspace.id:
            raise ValidationError({"client": "Client organization must belong to this workspace."})
    else:
        if client is not None:
            raise ValidationError({"client": "Internal roles (admin, member) cannot be linked to a client organization."})

    normalized_email = email.strip().lower()

    # Check if target email belongs to an active member in this workspace
    existing_user = User.objects.filter(email__iexact=normalized_email).first()
    if existing_user and WorkspaceMember.objects.filter(workspace=workspace, user=existing_user, status='active').exists():
        raise ValidationError({"email": "User with this email is already an active member of this workspace."})

    # Check for existing pending invitation in this workspace
    if WorkspaceInvitation.objects.filter(
        workspace=workspace,
        email__iexact=normalized_email,
        status='pending'
    ).exists():
        raise ValidationError({"email": "An active pending invitation for this email already exists in this workspace."})

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = timezone.now() + timedelta(days=expires_in_days)

    with transaction.atomic():
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=normalized_email,
            role=role,
            client=client,
            token_hash=token_hash,
            invited_by=inviter,
            status='pending',
            expires_at=expires_at
        )
        return invitation, raw_token


def accept_invitation(raw_token: str, user) -> WorkspaceMember:
    """
    Atomically accepts an invitation with select_for_update() row locking.
    Validates token, expiry, email identity match, and replay protection in ONE continuous transaction.
    The row lock remains held continuously until membership creation and invitation status update are committed.
    """
    token_hash = hash_token(raw_token)
    is_expired = False

    with transaction.atomic():
        invitation = WorkspaceInvitation.objects.select_for_update().filter(
            token_hash=token_hash
        ).first()

        if not invitation:
            raise ValidationError({"token": "Invalid invitation token."})

        if invitation.status != 'pending':
            raise ValidationError({"token": f"Invitation is already {invitation.status}."})

        if timezone.now() >= invitation.expires_at:
            invitation.status = 'expired'
            invitation.save(update_fields=['status'])
            is_expired = True

        if not is_expired:
            # Identity verification
            if user.email.strip().lower() != invitation.email.strip().lower():
                raise ValidationError({"token": "This invitation was issued to a different email address."})

            workspace = invitation.workspace

            # Handle existing membership if any (with row lock on membership)
            existing_member = WorkspaceMember.objects.select_for_update().filter(
                workspace=workspace,
                user=user
            ).first()

            if existing_member:
                if existing_member.status == 'suspended':
                    raise ValidationError({"detail": "Your membership in this workspace is suspended. Please contact the owner."})
                # Already active: mark invite accepted and return membership
                invitation.status = 'accepted'
                invitation.accepted_at = timezone.now()
                invitation.save(update_fields=['status', 'accepted_at'])
                return existing_member

            # Check client reference validity if role is client
            client = invitation.client
            if invitation.role == 'client':
                if not client or client.workspace_id != workspace.id:
                    raise ValidationError({"detail": "The client organization linked to this invitation no longer exists."})

            # Create active workspace membership
            member = WorkspaceMember.objects.create(
                workspace=workspace,
                user=user,
                role=invitation.role,
                client=client,
                status='active'
            )

            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['status', 'accepted_at'])

            return member

    if is_expired:
        raise ValidationError({"token": "This invitation has expired."})


def revoke_invitation(workspace: Workspace, invitation_id: uuid.UUID, user) -> WorkspaceInvitation:
    """
    Revokes a pending invitation.
    """
    with transaction.atomic():
        invitation = WorkspaceInvitation.objects.select_for_update().filter(
            id=invitation_id,
            workspace=workspace
        ).first()

        if not invitation:
            raise ValidationError({"detail": "Invitation not found."})

        if invitation.status != 'pending':
            raise ValidationError({"detail": f"Cannot revoke an invitation that is already {invitation.status}."})

        invitation.status = 'revoked'
        invitation.save(update_fields=['status'])
        return invitation


def transfer_ownership(
    workspace: Workspace,
    current_owner,
    new_owner_id: uuid.UUID
) -> Workspace:
    """
    Atomically transfers workspace ownership with select_for_update() row locking.
    Validates current owner identity, active status of both parties, and demotes old owner to Admin.
    """
    with transaction.atomic():
        ws = Workspace.objects.select_for_update().filter(id=workspace.id).first()
        if not ws:
            raise ValidationError({"detail": "Workspace not found."})

        if ws.owner_id != current_owner.id:
            raise PermissionDenied("Only the workspace owner can transfer ownership.")

        if current_owner.id == new_owner_id:
            raise ValidationError({"new_owner_id": "Cannot transfer ownership to yourself."})

        members = WorkspaceMember.objects.select_for_update().filter(
            workspace=ws,
            user_id__in=[current_owner.id, new_owner_id]
        )

        old_member = members.filter(user=current_owner, role='owner', status='active').first()
        if not old_member:
            raise ValidationError({"detail": "Current owner active membership record not found."})

        new_member = members.filter(user_id=new_owner_id, status='active').first()
        if not new_member:
            raise ValidationError({"new_owner_id": "Target user must be an active member of this workspace."})

        if new_member.role == 'client':
            raise ValidationError({"new_owner_id": "Client members cannot be made workspace owners."})

        # Demote previous owner to admin
        old_member.role = 'admin'
        old_member.client = None
        old_member.save(update_fields=['role', 'client'])

        # Promote new owner
        new_member.role = 'owner'
        new_member.client = None
        new_member.save(update_fields=['role', 'client'])

        # Update workspace owner pointer
        ws.owner = new_member.user
        ws.save(update_fields=['owner', 'updated_at'])

        return ws
