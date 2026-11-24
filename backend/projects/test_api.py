import uuid
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.test import APITestCase

from workspaces.models import Workspace, WorkspaceMember
from workspaces.services import create_workspace
from projects.models import Client, Project, ProjectMember

User = get_user_model()


class ProjectsAndClientsAPITests(APITestCase):
    def setUp(self):
        # Users
        self.owner = User.objects.create_user(
            email='p-owner@handoff.design',
            password='Password123!',
            first_name='Project',
            last_name='Owner'
        )
        self.admin_user = User.objects.create_user(
            email='p-admin@handoff.design',
            password='Password123!',
            first_name='Project',
            last_name='Admin'
        )
        self.member_user = User.objects.create_user(
            email='p-member@handoff.design',
            password='Password123!',
            first_name='Project',
            last_name='Member'
        )
        self.client_user_1 = User.objects.create_user(
            email='p-client1@handoff.design',
            password='Password123!',
            first_name='Client',
            last_name='One'
        )
        self.client_user_2 = User.objects.create_user(
            email='p-client2@handoff.design',
            password='Password123!',
            first_name='Client',
            last_name='Two'
        )
        self.outsider = User.objects.create_user(
            email='p-outsider@handoff.design',
            password='Password123!',
            first_name='Outsider',
            last_name='User'
        )

        # Primary Workspace
        self.workspace = create_workspace(user=self.owner, name='Creative Agency')
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.admin_user, role='admin', status='active')
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.member_user, role='member', status='active')

        # Clients in Workspace
        self.client_org_1 = Client.objects.create(workspace=self.workspace, name='Nike')
        self.client_org_2 = Client.objects.create(workspace=self.workspace, name='Adidas')

        # Client workspace memberships
        self.client_member_1 = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.client_user_1,
            role='client',
            client=self.client_org_1,
            status='active'
        )
        self.client_member_2 = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.client_user_2,
            role='client',
            client=self.client_org_2,
            status='active'
        )

        # Projects in Workspace
        # Project 1: Nike - Client User 1 assigned as ProjectMember
        self.project_nike_assigned = Project.objects.create(
            workspace=self.workspace,
            client=self.client_org_1,
            name='Nike Air Campaign',
            created_by=self.owner
        )
        ProjectMember.objects.create(
            project=self.project_nike_assigned,
            user=self.client_user_1,
            role='client'
        )

        # Project 2: Nike - Client User 1 NOT assigned
        self.project_nike_unassigned = Project.objects.create(
            workspace=self.workspace,
            client=self.client_org_1,
            name='Nike Internal Assets',
            created_by=self.owner
        )

        # Project 3: Adidas - Client User 2 assigned
        self.project_adidas = Project.objects.create(
            workspace=self.workspace,
            client=self.client_org_2,
            name='Adidas Originals Campaign',
            created_by=self.owner
        )
        ProjectMember.objects.create(
            project=self.project_adidas,
            user=self.client_user_2,
            role='client'
        )

        # Secondary (Other) Workspace
        self.other_workspace = create_workspace(user=self.outsider, name='Other Studio')
        self.other_client = Client.objects.create(workspace=self.other_workspace, name='Puma')
        self.other_project = Project.objects.create(
            workspace=self.other_workspace,
            client=self.other_client,
            name='Puma Suede Launch',
            created_by=self.outsider
        )

    # -------------------------------------------------------------
    # Clients API & RBAC
    # -------------------------------------------------------------
    def test_internal_member_can_list_and_create_clients(self):
        """Internal members (owner, admin, member) can access clients."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/clients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 2)

        # Create client
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/clients/',
            {'name': 'Under Armour', 'contact_email': 'contact@underarmour.com'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Under Armour')

    def test_client_role_cannot_access_clients_endpoint(self):
        """Client role users cannot list or create clients (403 Forbidden)."""
        self.client.force_authenticate(user=self.client_user_1)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/clients/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/clients/',
            {'name': 'Hacked Client'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_client_duplicate_name_case_insensitive_rejected(self):
        """Cannot create client with same name (case-insensitive) in same workspace."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/clients/',
            {'name': 'NIKE'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_client_detail_cross_workspace_idor_returns_404(self):
        """Accessing a client from another workspace returns 404."""
        self.client.force_authenticate(user=self.admin_user)
        # Attempt to access other_client (which belongs to other_workspace) via primary workspace URL
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/clients/{self.other_client.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Attempt to access other_workspace directly
        response = self.client.get(f'/api/v1/workspaces/{self.other_workspace.id}/clients/{self.other_client.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_client_protected_when_members_exist(self):
        """Deleting a client with associated members returns 400 Bad Request and raises ProtectedError in ORM."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/clients/{self.client_org_1.id}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Direct ORM deletion raises ProtectedError
        with self.assertRaises(ProtectedError):
            self.client_org_1.delete()

    # -------------------------------------------------------------
    # Projects API & Tenant Isolation
    # -------------------------------------------------------------
    def test_internal_members_see_all_workspace_projects(self):
        """Internal members see all projects within their workspace."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 3)

    def test_client_user_sees_ONLY_assigned_projects_of_own_client(self):
        """
        Client user visibility is strictly scoped:
        - Only projects belonging to their Client organization
        - AND only projects where they are explicitly assigned in ProjectMember
        """
        self.client.force_authenticate(user=self.client_user_1)
        response = self.client.get(f'/api/v1/workspaces/{self.workspace.id}/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data

        # Should ONLY see project_nike_assigned (1 project)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(self.project_nike_assigned.id))

        # Direct GET on unassigned Nike project returns 404 (IDOR protection)
        detail_unassigned = self.client.get(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_unassigned.id}/'
        )
        self.assertEqual(detail_unassigned.status_code, status.HTTP_404_NOT_FOUND)

        # Direct GET on Adidas project returns 404 (Cross-client IDOR protection)
        detail_adidas = self.client.get(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_adidas.id}/'
        )
        self.assertEqual(detail_adidas.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_role_cannot_create_or_modify_projects(self):
        """Client users have read-only access (POST/PATCH/DELETE returns 403)."""
        self.client.force_authenticate(user=self.client_user_1)

        # POST
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/',
            {'name': 'Unauthorized Project'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # PATCH
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_assigned.id}/',
            {'name': 'Tampered Name'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE
        response = self.client.delete(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_assigned.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_workspace_project_idor_returns_404(self):
        """Querying, patching, or deleting a project from another workspace returns 404."""
        self.client.force_authenticate(user=self.admin_user)

        # GET
        response = self.client.get(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.other_project.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH
        response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.other_project.id}/',
            {'name': 'Cross WS Attack'}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE
        response = self.client.delete(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.other_project.id}/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_project_cross_workspace_client_tampering_rejected(self):
        """Cannot assign a client from Workspace B to a project in Workspace A."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/',
            {
                'name': 'Tampered Project',
                'client': str(self.other_client.id)
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('client', response.data)

    # -------------------------------------------------------------
    # Project Members API
    # -------------------------------------------------------------
    def test_add_project_member_requires_active_workspace_membership(self):
        """User must be an active workspace member to be assigned to a project."""
        self.client.force_authenticate(user=self.admin_user)
        # Attempt to add outsider (not in workspace)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_assigned.id}/members/',
            {
                'user_id': str(self.outsider.id),
                'role': 'collaborator'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', response.data)

    def test_add_client_user_to_unrelated_project_rejected(self):
        """Client member from Adidas cannot be added to a Nike project."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_assigned.id}/members/',
            {
                'user_id': str(self.client_user_2.id),  # Adidas client user
                'role': 'client'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', response.data)

    def test_add_client_user_with_internal_role_rejected(self):
        """Client workspace member cannot be given internal project roles (lead/collaborator/reviewer)."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_unassigned.id}/members/',
            {
                'user_id': str(self.client_user_1.id),
                'role': 'collaborator'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_add_internal_user_with_client_role_rejected(self):
        """Internal workspace member cannot be given client role on project."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.project_nike_unassigned.id}/members/',
            {
                'user_id': str(self.member_user.id),
                'role': 'client'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_cross_workspace_project_member_idor_returns_404(self):
        """Accessing project members across workspace boundary returns 404."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            f'/api/v1/workspaces/{self.workspace.id}/projects/{self.other_project.id}/members/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
