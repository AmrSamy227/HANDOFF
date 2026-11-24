import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.functions import Lower


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=150)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    company_website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                'workspace',
                name='unique_client_name_ci_per_workspace'
            )
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"


class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('in_review', 'In Review'),
        ('changes_requested', 'Changes Requested'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='projects')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_projects')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                'workspace',
                name='unique_project_name_ci_per_workspace'
            )
        ]
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['workspace', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.workspace.name}]"


class ProjectMember(models.Model):
    PROJECT_ROLES = [
        ('lead', 'Lead'),
        ('collaborator', 'Collaborator'),
        ('reviewer', 'Reviewer'),
        ('client', 'Client Reviewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=PROJECT_ROLES, default='collaborator')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_user_per_project')
        ]

    def __str__(self):
        return f"{self.user} as {self.role} on {self.project.name}"
