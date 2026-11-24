import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q
from django.db.models.functions import Lower


class Workspace(models.Model):
    WORKSPACE_TYPES = [
        ('personal', 'Personal'),
        ('agency', 'Agency'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True)
    workspace_type = models.CharField(max_length=20, choices=WORKSPACE_TYPES, default='personal')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_workspaces'
    )
    logo = models.ImageField(upload_to='workspaces/logos/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name[:80]) or 'workspace'
            unique_suffix = uuid.uuid4().hex[:8]
            self.slug = f"{base_slug}-{unique_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class WorkspaceMember(models.Model):
    ROLES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('client', 'Client'),
    ]
    STATUSES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLES, default='member')
    status = models.CharField(max_length=20, choices=STATUSES, default='active')
    client = models.ForeignKey(
        'projects.Client',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='associated_workspace_members'
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'user'], name='unique_workspace_user_membership'),
            models.CheckConstraint(
                condition=(
                    (Q(role='client') & Q(client__isnull=False)) |
                    (~Q(role='client') & Q(client__isnull=True))
                ),
                name='workspace_member_role_client_consistency'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['workspace', 'role']),
        ]

    def __str__(self):
        return f"{self.user} ({self.role}) in {self.workspace}"


class WorkspaceInvitation(models.Model):
    INVITABLE_ROLES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('client', 'Client'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=INVITABLE_ROLES, default='member')
    client = models.ForeignKey('projects.Client', null=True, blank=True, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                'workspace',
                condition=Q(status='pending'),
                name='unique_pending_invitation_email_ci_per_workspace'
            ),
            models.CheckConstraint(
                condition=(
                    (Q(role='client') & Q(client__isnull=False)) |
                    (~Q(role='client') & Q(client__isnull=True))
                ),
                name='workspace_invitation_role_client_consistency'
            ),
        ]
        indexes = [
            models.Index(fields=['workspace', 'status']),
        ]

    @property
    def is_valid(self):
        return self.status == 'pending' and timezone.now() < self.expires_at

    def __str__(self):
        return f"Invite {self.email} as {self.role} to {self.workspace}"
