from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from workspaces.models import Workspace
from projects.models import Client, Project, ProjectMember

User = get_user_model()


class ClientModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='client-tester@handoff.design',
            password='Password123!'
        )
        self.workspace1 = Workspace.objects.create(
            name='Agency Alpha',
            owner=self.user
        )
        self.workspace2 = Workspace.objects.create(
            name='Agency Beta',
            owner=self.user
        )

    def test_client_creation_success(self):
        """Client is created successfully with workspace link."""
        client = Client.objects.create(
            workspace=self.workspace1,
            name='Global Dynamics',
            contact_email='contact@globaldynamics.com',
            contact_phone='+1-555-0199',
            company_website='https://globaldynamics.com',
            notes='Key enterprise client'
        )
        self.assertEqual(client.name, 'Global Dynamics')
        self.assertEqual(str(client), f"Global Dynamics ({self.workspace1.name})")

    def test_unique_client_name_ci_per_workspace(self):
        """Client name is case-insensitively unique within a workspace."""
        Client.objects.create(
            workspace=self.workspace1,
            name='Stark Industries'
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Client.objects.create(
                    workspace=self.workspace1,
                    name='stark industries'
                )

    def test_same_client_name_allowed_in_different_workspaces(self):
        """Different workspaces can have clients with the same name."""
        c1 = Client.objects.create(workspace=self.workspace1, name='Wayne Enterprises')
        c2 = Client.objects.create(workspace=self.workspace2, name='Wayne Enterprises')
        self.assertNotEqual(c1.workspace, c2.workspace)

    def test_workspace_deletion_cascades_to_clients(self):
        """Deleting a workspace cascades and deletes all associated clients."""
        Client.objects.create(workspace=self.workspace1, name='Cyberdyne')
        self.assertEqual(Client.objects.filter(workspace=self.workspace1).count(), 1)
        self.workspace1.delete()
        self.assertEqual(Client.objects.filter(name='Cyberdyne').count(), 0)


class ProjectModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='project-tester@handoff.design',
            password='Password123!'
        )
        self.workspace1 = Workspace.objects.create(
            name='Workspace One',
            owner=self.user
        )
        self.workspace2 = Workspace.objects.create(
            name='Workspace Two',
            owner=self.user
        )
        self.client_org = Client.objects.create(
            workspace=self.workspace1,
            name='Client One'
        )

    def test_project_creation_success(self):
        """Project is created with default status 'planning'."""
        project = Project.objects.create(
            workspace=self.workspace1,
            client=self.client_org,
            name='Q4 Brand Campaign',
            description='Complete visual assets overhaul',
            created_by=self.user
        )
        self.assertEqual(project.status, 'planning')
        self.assertEqual(str(project), f"Q4 Brand Campaign [{self.workspace1.name}]")

    def test_unique_project_name_ci_per_workspace(self):
        """Project name is case-insensitively unique within a workspace."""
        Project.objects.create(
            workspace=self.workspace1,
            name='Mobile App Redesign'
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Project.objects.create(
                    workspace=self.workspace1,
                    name='mobile app redesign'
                )

    def test_same_project_name_allowed_in_different_workspaces(self):
        """Different workspaces can have projects with the same name."""
        p1 = Project.objects.create(workspace=self.workspace1, name='Brand Identity')
        p2 = Project.objects.create(workspace=self.workspace2, name='Brand Identity')
        self.assertNotEqual(p1.workspace, p2.workspace)

    def test_deleting_client_sets_project_client_null(self):
        """Deleting a client does not delete the project; sets client to NULL."""
        project = Project.objects.create(
            workspace=self.workspace1,
            client=self.client_org,
            name='Product Launch'
        )
        self.client_org.delete()
        project.refresh_from_db()
        self.assertIsNone(project.client)

    def test_deleting_creator_user_sets_project_created_by_null(self):
        """Deleting creator user does not delete project; sets created_by to NULL."""
        creator = User.objects.create_user(
            email='creator@handoff.design',
            password='Password123!'
        )
        project = Project.objects.create(
            workspace=self.workspace1,
            name='Video Production',
            created_by=creator
        )
        creator.delete()
        project.refresh_from_db()
        self.assertIsNone(project.created_by)

    def test_deleting_workspace_cascades_to_projects(self):
        """Deleting a workspace cascades and deletes all associated projects."""
        Project.objects.create(workspace=self.workspace1, name='Workspace Project')
        self.assertEqual(Project.objects.filter(workspace=self.workspace1).count(), 1)
        self.workspace1.delete()
        self.assertEqual(Project.objects.filter(name='Workspace Project').count(), 0)


class ProjectMemberModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='pm-owner@handoff.design',
            password='Password123!'
        )
        self.member1 = User.objects.create_user(
            email='pm-member1@handoff.design',
            password='Password123!'
        )
        self.workspace = Workspace.objects.create(
            name='PM Studio',
            owner=self.owner
        )
        self.project = Project.objects.create(
            workspace=self.workspace,
            name='Brand Design',
            created_by=self.owner
        )

    def test_project_member_creation_success(self):
        """Project member can be assigned roles."""
        pm = ProjectMember.objects.create(
            project=self.project,
            user=self.member1,
            role='lead'
        )
        self.assertEqual(pm.role, 'lead')
        self.assertEqual(str(pm), f"{self.member1} as lead on {self.project.name}")

    def test_unique_user_per_project_constraint(self):
        """A user cannot be added twice to the same project."""
        ProjectMember.objects.create(
            project=self.project,
            user=self.member1,
            role='collaborator'
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProjectMember.objects.create(
                    project=self.project,
                    user=self.member1,
                    role='reviewer'
                )

    def test_deleting_project_cascades_to_project_members(self):
        """Deleting a project cascades and deletes its member assignments."""
        ProjectMember.objects.create(
            project=self.project,
            user=self.member1,
            role='collaborator'
        )
        self.assertEqual(ProjectMember.objects.filter(project=self.project).count(), 1)
        self.project.delete()
        self.assertEqual(ProjectMember.objects.filter(user=self.member1).count(), 0)

    def test_deleting_user_cascades_to_project_members(self):
        """Deleting a user cascades and deletes their project member records."""
        ProjectMember.objects.create(
            project=self.project,
            user=self.member1,
            role='reviewer'
        )
        self.member1.delete()
        self.assertEqual(ProjectMember.objects.filter(project=self.project).count(), 0)
