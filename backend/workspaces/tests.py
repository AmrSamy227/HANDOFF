import hashlib
import secrets
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone
from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from projects.models import Client

User = get_user_model()


class WorkspaceModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@handoff.design',
            password='Password123!',
            first_name='Owner',
            last_name='User'
        )

    def test_workspace_creation_with_auto_generated_slug(self):
        """Workspace creates an auto-generated unique slug with name prefix and hex suffix."""
        workspace = Workspace.objects.create(
            name='Acme Design Studio',
            owner=self.owner,
            workspace_type='agency'
        )
        self.assertTrue(workspace.slug.startswith('acme-design-studio-'))
        self.assertEqual(len(workspace.slug.split('-')[-1]), 8)
        self.assertEqual(str(workspace), 'Acme Design Studio')

    def test_workspace_preserves_explicit_slug(self):
        """Explicitly provided slug is not overwritten."""
        workspace = Workspace.objects.create(
            name='Custom Studio',
            slug='my-custom-slug',
            owner=self.owner
        )
        self.assertEqual(workspace.slug, 'my-custom-slug')

    def test_owner_is_protected_from_deletion(self):
        """Deleting an owner who has workspaces raises ProtectedError."""
        Workspace.objects.create(
            name='Protected Studio',
            owner=self.owner
        )
        with self.assertRaises(ProtectedError):
            self.owner.delete()


class WorkspaceMemberModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='ws-owner@handoff.design',
            password='Password123!',
            first_name='WS',
            last_name='Owner'
        )
        self.member_user = User.objects.create_user(
            email='ws-member@handoff.design',
            password='Password123!',
            first_name='WS',
            last_name='Member'
        )
        self.client_user = User.objects.create_user(
            email='ws-client@handoff.design',
            password='Password123!',
            first_name='WS',
            last_name='Client'
        )
        self.workspace = Workspace.objects.create(
            name='Studio X',
            owner=self.owner
        )
        self.client_org = Client.objects.create(
            name='Acme Corp',
            workspace=self.workspace
        )

    def test_create_internal_members_success(self):
        """Internal roles (owner, admin, member) can be created with client=None."""
        owner_member = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role='owner'
        )
        self.assertEqual(owner_member.role, 'owner')
        self.assertIsNone(owner_member.client)

        admin_member = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member_user,
            role='admin'
        )
        self.assertEqual(admin_member.role, 'admin')
        self.assertIsNone(admin_member.client)

    def test_create_client_role_with_client_success(self):
        """Client role member can be created when linked to a Client organization."""
        client_member = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.client_user,
            role='client',
            client=self.client_org
        )
        self.assertEqual(client_member.role, 'client')
        self.assertEqual(client_member.client, self.client_org)

    def test_unique_workspace_user_membership(self):
        """A user cannot have multiple memberships in the same workspace."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member_user,
            role='member'
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                WorkspaceMember.objects.create(
                    workspace=self.workspace,
                    user=self.member_user,
                    role='admin'
                )

    def test_client_role_requires_client_field(self):
        """Database CheckConstraint rejects role='client' when client is None."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                WorkspaceMember.objects.create(
                    workspace=self.workspace,
                    user=self.client_user,
                    role='client',
                    client=None
                )

    def test_internal_roles_reject_client_field(self):
        """Database CheckConstraint rejects internal roles (member, admin, owner) when client is not None."""
        for role in ('member', 'admin', 'owner'):
            user = User.objects.create_user(
                email=f'{role}-test@handoff.design',
                password='Password123!'
            )
            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    WorkspaceMember.objects.create(
                        workspace=self.workspace,
                        user=user,
                        role=role,
                        client=self.client_org
                    )

    def test_cascade_delete_workspace_deletes_memberships(self):
        """Deleting a workspace cascades and deletes its memberships."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member_user,
            role='member'
        )
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace).count(), 1)
        # Note: workspace.owner is protected, so remove or change owner constraint test
        # Workspace cascade:
        self.workspace.delete()
        self.assertEqual(WorkspaceMember.objects.filter(user=self.member_user).count(), 0)

    def test_cascade_delete_user_deletes_memberships(self):
        """Deleting a regular user cascades and deletes their workspace memberships."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member_user,
            role='member'
        )
        self.member_user.delete()
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace).count(), 0)

    def test_client_deletion_protected_when_has_associated_members(self):
        """Deleting a Client organization with associated WorkspaceMember records raises ProtectedError."""
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.client_user,
            role='client',
            client=self.client_org
        )
        with self.assertRaises(ProtectedError):
            self.client_org.delete()
        self.assertTrue(Client.objects.filter(id=self.client_org.id).exists())

    def test_client_deletion_succeeds_when_no_associated_members(self):
        """Deleting a Client organization without any associated WorkspaceMember records succeeds."""
        unassociated_client = Client.objects.create(
            workspace=self.workspace,
            name='Standalone Client'
        )
        unassociated_client_id = unassociated_client.id
        unassociated_client.delete()
        self.assertFalse(Client.objects.filter(id=unassociated_client_id).exists())


class WorkspaceInvitationModelTests(TestCase):
    def setUp(self):
        self.inviter = User.objects.create_user(
            email='inviter@handoff.design',
            password='Password123!',
            first_name='Inviter',
            last_name='User'
        )
        self.workspace = Workspace.objects.create(
            name='Invitation Studio',
            owner=self.inviter
        )
        self.client_org = Client.objects.create(
            name='Invitation Client',
            workspace=self.workspace
        )
        self.other_workspace = Workspace.objects.create(
            name='Other Studio',
            owner=self.inviter
        )

    def _hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    def test_create_invitation_success(self):
        """Successfully create a pending invitation."""
        raw_token = secrets.token_urlsafe(32)
        invitation = WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='collaborator@example.com',
            role='member',
            token_hash=self._hash_token(raw_token),
            invited_by=self.inviter,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(invitation.status, 'pending')
        self.assertTrue(invitation.is_valid)

    def test_unique_pending_invitation_ci_email_per_workspace(self):
        """Cannot have two pending invitations for the same email (case-insensitive) in the same workspace."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='invitee@example.com',
            role='member',
            token_hash=self._hash_token(token1),
            invited_by=self.inviter,
            expires_at=timezone.now() + timedelta(days=7)
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                WorkspaceInvitation.objects.create(
                    workspace=self.workspace,
                    email='INVITEE@EXAMPLE.COM',
                    role='admin',
                    token_hash=self._hash_token(token2),
                    invited_by=self.inviter,
                    expires_at=timezone.now() + timedelta(days=7)
                )

    def test_allows_reinvite_after_previous_invitation_accepted_or_expired(self):
        """If previous invite is accepted or expired, a new pending invite for the same email is allowed."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='reinvite@example.com',
            role='member',
            token_hash=self._hash_token(token1),
            invited_by=self.inviter,
            status='accepted',
            expires_at=timezone.now() + timedelta(days=7)
        )

        new_invitation = WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='reinvite@example.com',
            role='member',
            token_hash=self._hash_token(token2),
            invited_by=self.inviter,
            status='pending',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(new_invitation.status, 'pending')

    def test_allows_same_email_pending_invite_in_different_workspaces(self):
        """The same email can have pending invitations in two separate workspaces."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='dual-invite@example.com',
            role='member',
            token_hash=self._hash_token(token1),
            invited_by=self.inviter,
            expires_at=timezone.now() + timedelta(days=7)
        )

        invite_ws2 = WorkspaceInvitation.objects.create(
            workspace=self.other_workspace,
            email='dual-invite@example.com',
            role='member',
            token_hash=self._hash_token(token2),
            invited_by=self.inviter,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(invite_ws2.workspace, self.other_workspace)

    def test_invitation_client_role_requires_client_field(self):
        """Database CheckConstraint rejects invitation with role='client' when client is None."""
        token = secrets.token_urlsafe(32)
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                WorkspaceInvitation.objects.create(
                    workspace=self.workspace,
                    email='client-invite@example.com',
                    role='client',
                    client=None,
                    token_hash=self._hash_token(token),
                    invited_by=self.inviter,
                    expires_at=timezone.now() + timedelta(days=7)
                )

    def test_invitation_client_role_with_client_success(self):
        """Invitation with role='client' succeeds when client is provided."""
        token = secrets.token_urlsafe(32)
        invitation = WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='client-invite@example.com',
            role='client',
            client=self.client_org,
            token_hash=self._hash_token(token),
            invited_by=self.inviter,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(invitation.role, 'client')
        self.assertEqual(invitation.client, self.client_org)

    def test_invitation_internal_roles_reject_client_field(self):
        """Database CheckConstraint rejects invitation with role='admin' or 'member' when client is not None."""
        for role in ('admin', 'member'):
            token = secrets.token_urlsafe(32)
            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    WorkspaceInvitation.objects.create(
                        workspace=self.workspace,
                        email=f'{role}-fail@example.com',
                        role=role,
                        client=self.client_org,
                        token_hash=self._hash_token(token),
                        invited_by=self.inviter,
                        expires_at=timezone.now() + timedelta(days=7)
                    )

    def test_is_valid_property(self):
        """Check is_valid property logic."""
        token = secrets.token_urlsafe(32)
        valid_invitation = WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            email='valid@example.com',
            role='member',
            token_hash=self._hash_token(token),
            invited_by=self.inviter,
            status='pending',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertTrue(valid_invitation.is_valid)

        # Expired
        valid_invitation.expires_at = timezone.now() - timedelta(hours=1)
        valid_invitation.save()
        self.assertFalse(valid_invitation.is_valid)

        # Non-pending status
        valid_invitation.expires_at = timezone.now() + timedelta(hours=1)
        valid_invitation.status = 'accepted'
        valid_invitation.save()
        self.assertFalse(valid_invitation.is_valid)
