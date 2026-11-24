import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspaces.services import create_workspace, create_invitation
from projects.models import Client

User = get_user_model()


class WorkspaceAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='api-owner@handoff.design',
            password='Password123!',
            first_name='Owner',
            last_name='User'
        )
        self.admin_user = User.objects.create_user(
            email='api-admin@handoff.design',
            password='Password123!',
            first_name='Admin',
            last_name='User'
        )
        self.member_user = User.objects.create_user(
            email='api-member@handoff.design',
            password='Password123!',
            first_name='Member',
            last_name='User'
        )
        self.outsider = User.objects.create_user(
            email='api-outsider@handoff.design',
            password='Password123!',
            first_name='Outsider',
            last_name='User'
        )
        self.workspace = create_workspace(user=self.owner, name='API Workspace')
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.admin_user,
            role='admin',
            status='active'
        )
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member_user,
            role='member',
            status='active'
        )

        # Other workspace
        self.other_workspace = create_workspace(user=self.outsider, name='Other Workspace')

    # -------------------------------------------------------------
    # Workspace List & Create
    # -------------------------------------------------------------
    def test_unauthenticated_cannot_access_workspaces(self):
        """Unauthenticated requests receive 401 Unauthorized."""
        response = self.client.get('/api/v1/workspaces/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_workspaces_tenant_isolation(self):
        """User only receives workspaces they actively belong to."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get('/api/v1/workspaces/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.workspace.id))
        self.assertEqual(results[0]['user_role'], 'member')

    def test_create_workspace_api(self):
        """POST /api/v1/workspaces/ creates workspace and assigns creator as Owner."""
        self.client.force_authenticate(user=self.outsider)
        payload = {'name': 'Outsider New Studio', 'workspace_type': 'agency'}
        response = self.client.post('/api/v1/workspaces/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Outsider New Studio')
        self.assertEqual(response.data['user_role'], 'owner')

    def test_workspace_detail_idor_protection(self):
        """Accessing a workspace the user does not belong to returns 404."""
        self.client.force_authenticate(user=self.member_user)
        # Attempt to access other_workspace
        response = self.client.get(f'/api/v1/workspaces/{self.other_workspace.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_workspace_permissions(self):
        """Admin can update workspace; regular member receives 403."""
        # Regular member
        self.client.force_authenticate(user=self.member_user)
        response = self.client.patch(f'/api/v1/workspaces/{self.workspace.id}/', {'name': 'Hacked Name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(f'/api/v1/workspaces/{self.workspace.id}/', {'name': 'Updated Studio Name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Studio Name')

    def test_delete_workspace_permissions(self):
        """Only owner can delete workspace; admin receives 403."""
        # Admin attempt
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Owner attempt
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_transfer_ownership_api(self):
        """Owner can transfer ownership; non-owner is rejected."""
        # Member attempt
        self.client.force_authenticate(user=self.member_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/transfer-ownership/',
            {'new_owner_id': str(self.admin_user.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Owner attempt
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/transfer-ownership/',
            {'new_owner_id': str(self.admin_user.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.owner, self.admin_user)

    # -------------------------------------------------------------
    # Workspace Members
    # -------------------------------------------------------------
    def test_list_members_active_member_allowed(self):
        """Active members can list workspace members."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/members/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 3)

    def test_suspended_member_gets_404(self):
        """Suspended member querying workspace gets 404."""
        member_record = WorkspaceMember.objects.get(workspace=self.workspace, user=self.member_user)
        member_record.status = 'suspended'
        member_record.save()

        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/members/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_member_role_admin_allowed_owner_protected(self):
        """Admin can promote member; cannot change or suspend Owner directly."""
        self.client.force_authenticate(user=self.admin_user)
        member_record = WorkspaceMember.objects.get(workspace=self.workspace, user=self.member_user)
        owner_record = WorkspaceMember.objects.get(workspace=self.workspace, user=self.owner)

        # Promote member to admin
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/members/{member_record.id}/',
            {'role': 'admin'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'admin')

        # Attempt to change owner role directly
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/members/{owner_record.id}/',
            {'role': 'member'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt to suspend owner
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/members/{owner_record.id}/',
            {'status': 'suspended'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Attempt to assign owner role directly
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/members/{member_record.id}/',
            {'role': 'owner'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_member_permissions(self):
        """Admin can delete regular member; cannot delete owner."""
        self.client.force_authenticate(user=self.admin_user)
        member_record = WorkspaceMember.objects.get(workspace=self.workspace, user=self.member_user)
        owner_record = WorkspaceMember.objects.get(workspace=self.workspace, user=self.owner)

        # Attempt to delete owner
        response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/members/{owner_record.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Delete regular member
        response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/members/{member_record.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # -------------------------------------------------------------
    # Invitations API
    # -------------------------------------------------------------
    def test_create_and_accept_invitation_api_flow(self):
        """Full invitation lifecycle: create (admin), return raw_token, accept (/api/v1/invitations/accept/)."""
        # Create invitation as Admin
        self.client.force_authenticate(user=self.admin_user)
        invitee = User.objects.create_user(
            email='new-person@handoff.design',
            password='Password123!'
        )
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/invitations/',
            {'email': invitee.email, 'role': 'member'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('raw_token', response.data)
        raw_token = response.data['raw_token']

        # Accept invitation as invitee
        self.client.force_authenticate(user=invitee)
        accept_response = self.client.post(
            '/api/v1/invitations/accept/',
            {'token': raw_token}
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertEqual(accept_response.data['role'], 'member')
        self.assertEqual(accept_response.data['status'], 'active')

        # Check membership exists
        self.assertTrue(
            WorkspaceMember.objects.filter(workspace=self.workspace, user=invitee, status='active').exists()
        )

    def test_revoke_invitation_api(self):
        """Admin can revoke invitation."""
        self.client.force_authenticate(user=self.admin_user)
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.admin_user,
            email='revokeme@handoff.design',
            role='member'
        )
        response = self.client.post(f'/api/v1/workspaces/{self.workspace.id}/invitations/{invitation.id}/revoke/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'revoked')
