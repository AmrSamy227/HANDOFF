import hashlib
import secrets
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspaces.services import (
    create_workspace,
    create_invitation,
    accept_invitation,
    revoke_invitation,
    transfer_ownership,
    hash_token,
)
from projects.models import Client

User = get_user_model()


class WorkspaceServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='ws-owner@handoff.design',
            password='Password123!',
            first_name='Owner',
            last_name='User'
        )
        self.admin_user = User.objects.create_user(
            email='ws-admin@handoff.design',
            password='Password123!',
            first_name='Admin',
            last_name='User'
        )
        self.member_user = User.objects.create_user(
            email='ws-member@handoff.design',
            password='Password123!',
            first_name='Member',
            last_name='User'
        )
        self.client_user = User.objects.create_user(
            email='ws-client@handoff.design',
            password='Password123!',
            first_name='Client',
            last_name='User'
        )
        self.workspace = create_workspace(
            user=self.owner,
            name='Design Studio One',
            workspace_type='agency'
        )
        self.client_org = Client.objects.create(
            workspace=self.workspace,
            name='Acme Global'
        )
        self.other_workspace = create_workspace(
            user=self.owner,
            name='Design Studio Two'
        )
        self.other_client_org = Client.objects.create(
            workspace=self.other_workspace,
            name='Other Client'
        )

    # -------------------------------------------------------------
    # Workspace Creation Atomicity
    # -------------------------------------------------------------
    def test_create_workspace_service_atomicity(self):
        """Creates workspace and assigns owner membership atomically."""
        ws = create_workspace(user=self.admin_user, name='Atomic Studio')
        self.assertEqual(ws.owner, self.admin_user)
        membership = WorkspaceMember.objects.filter(workspace=ws, user=self.admin_user).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, 'owner')
        self.assertEqual(membership.status, 'active')
        self.assertIsNone(membership.client)

    # -------------------------------------------------------------
    # Invitation Creation & Hashing
    # -------------------------------------------------------------
    def test_create_invitation_hashes_token_and_stores_no_raw_token(self):
        """Raw token is returned to caller but only SHA-256 hash is persisted."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email='new-collaborator@example.com',
            role='member'
        )
        self.assertIsNotNone(raw_token)
        self.assertEqual(invitation.token_hash, hash_token(raw_token))
        self.assertNotEqual(invitation.token_hash, raw_token)

        # Check DB directly
        db_invitation = WorkspaceInvitation.objects.get(id=invitation.id)
        self.assertEqual(db_invitation.token_hash, hash_token(raw_token))

    def test_create_invitation_rejects_owner_role(self):
        """Cannot invite user as owner."""
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email='fake-owner@example.com',
                role='owner'
            )
        self.assertIn('role', ctx.exception.detail)

    def test_create_invitation_enforces_role_client_consistency(self):
        """Client role requires client org from same workspace; internal roles forbid client org."""
        # Client role without client
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email='c1@example.com',
                role='client',
                client=None
            )
        self.assertIn('client', ctx.exception.detail)

        # Client role with client from another workspace
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email='c2@example.com',
                role='client',
                client=self.other_client_org
            )
        self.assertIn('client', ctx.exception.detail)

        # Internal role with client org
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email='c3@example.com',
                role='member',
                client=self.client_org
            )
        self.assertIn('client', ctx.exception.detail)

    def test_create_invitation_rejects_already_active_member(self):
        """Cannot invite an email that belongs to an active member in this workspace."""
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email=self.owner.email,
                role='admin'
            )
        self.assertIn('email', ctx.exception.detail)

    def test_create_invitation_rejects_duplicate_pending(self):
        """Cannot create duplicate pending invitations for same email (case-insensitive)."""
        create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email='invite-duplicate@example.com',
            role='member'
        )
        with self.assertRaises(ValidationError) as ctx:
            create_invitation(
                workspace=self.workspace,
                inviter=self.owner,
                email='INVITE-DUPLICATE@EXAMPLE.COM',
                role='admin'
            )
        self.assertIn('email', ctx.exception.detail)

    # -------------------------------------------------------------
    # Invitation Acceptance & Replay Protection
    # -------------------------------------------------------------
    def test_accept_invitation_success(self):
        """Accepting a valid invitation creates active membership and updates status."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email=self.member_user.email,
            role='member'
        )
        membership = accept_invitation(raw_token=raw_token, user=self.member_user)
        self.assertEqual(membership.workspace, self.workspace)
        self.assertEqual(membership.user, self.member_user)
        self.assertEqual(membership.role, 'member')
        self.assertEqual(membership.status, 'active')

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'accepted')
        self.assertIsNotNone(invitation.accepted_at)

    def test_accept_invitation_identity_mismatch_rejected(self):
        """User whose email does not match invitation cannot accept it."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email='intended-recipient@example.com',
            role='member'
        )
        with self.assertRaises(ValidationError) as ctx:
            accept_invitation(raw_token=raw_token, user=self.member_user)
        self.assertIn('token', ctx.exception.detail)

    def test_accept_invitation_expired_rejected(self):
        """Expired invitations cannot be accepted."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email=self.member_user.email,
            role='member'
        )
        # Manually expire
        invitation.expires_at = timezone.now() - timedelta(minutes=5)
        invitation.save()

        with self.assertRaises(ValidationError) as ctx:
            accept_invitation(raw_token=raw_token, user=self.member_user)
        self.assertIn('token', ctx.exception.detail)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'expired')

    def test_accept_invitation_replay_attack_rejected(self):
        """Replaying an already accepted invitation token is rejected."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email=self.member_user.email,
            role='member'
        )
        accept_invitation(raw_token=raw_token, user=self.member_user)

        with self.assertRaises(ValidationError) as ctx:
            accept_invitation(raw_token=raw_token, user=self.member_user)
        self.assertIn('token', ctx.exception.detail)

    def test_revoke_invitation(self):
        """Admin/owner can revoke a pending invitation."""
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email='revoke-me@example.com',
            role='member'
        )
        revoked = revoke_invitation(
            workspace=self.workspace,
            invitation_id=invitation.id,
            user=self.owner
        )
        self.assertEqual(revoked.status, 'revoked')

        # Cannot accept revoked invitation
        user = User.objects.create_user(email='revoke-me@example.com', password='Password123!')
        with self.assertRaises(ValidationError):
            accept_invitation(raw_token=raw_token, user=user)

    # -------------------------------------------------------------
    # Ownership Transfer
    # -------------------------------------------------------------
    def test_transfer_ownership_success(self):
        """Ownership transfer demotes old owner to Admin and promotes new owner."""
        # Add admin_user as active member
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.admin_user,
            role='admin',
            status='active'
        )
        updated_ws = transfer_ownership(
            workspace=self.workspace,
            current_owner=self.owner,
            new_owner_id=self.admin_user.id
        )
        self.assertEqual(updated_ws.owner, self.admin_user)

        old_member = WorkspaceMember.objects.get(workspace=self.workspace, user=self.owner)
        self.assertEqual(old_member.role, 'admin')

        new_member = WorkspaceMember.objects.get(workspace=self.workspace, user=self.admin_user)
        self.assertEqual(new_member.role, 'owner')

    def test_transfer_ownership_to_self_rejected(self):
        """Cannot transfer ownership to self."""
        with self.assertRaises(ValidationError) as ctx:
            transfer_ownership(
                workspace=self.workspace,
                current_owner=self.owner,
                new_owner_id=self.owner.id
            )
        self.assertIn('new_owner_id', ctx.exception.detail)

    def test_transfer_ownership_by_non_owner_rejected(self):
        """Non-owner calling transfer raises PermissionDenied."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.admin_user,
            role='admin',
            status='active'
        )
        with self.assertRaises(PermissionDenied):
            transfer_ownership(
                workspace=self.workspace,
                current_owner=self.admin_user,
                new_owner_id=self.owner.id
            )

    def test_transfer_ownership_to_client_member_rejected(self):
        """Client role member cannot be made owner."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.client_user,
            role='client',
            client=self.client_org,
            status='active'
        )
        with self.assertRaises(ValidationError) as ctx:
            transfer_ownership(
                workspace=self.workspace,
                current_owner=self.owner,
                new_owner_id=self.client_user.id
            )
        self.assertIn('new_owner_id', ctx.exception.detail)
