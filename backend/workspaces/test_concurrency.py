import threading
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from workspaces.models import Workspace, WorkspaceMember, WorkspaceInvitation
from workspaces.services import create_workspace, create_invitation

User = get_user_model()


class ConcurrentInvitationAcceptanceTests(TransactionTestCase):
    """
    Validates PostgreSQL row locking during simultaneous invitation acceptance.
    Uses TransactionTestCase and separate database connections across threads.
    """
    def setUp(self):
        self.owner = User.objects.create_user(
            email='conc-owner@handoff.design',
            password='Password123!',
            first_name='Owner',
            last_name='User'
        )
        self.invitee = User.objects.create_user(
            email='conc-invitee@handoff.design',
            password='Password123!',
            first_name='Invitee',
            last_name='User'
        )
        self.workspace = create_workspace(user=self.owner, name='Concurrency Workspace')

    def test_concurrent_invitation_acceptance(self):
        """
        Simulate two simultaneous HTTP requests accepting the same invitation token.
        Uses threading.Barrier to ensure both threads synchronize and execute their requests concurrently.
        """
        # Create a pending invitation
        invitation, raw_token = create_invitation(
            workspace=self.workspace,
            inviter=self.owner,
            email=self.invitee.email,
            role='member'
        )

        # Barrier for 2 threads to start their accept request simultaneously
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker():
            try:
                # Each thread gets its own independent Django/PostgreSQL DB connection
                connection.close()

                client = APIClient()
                client.force_authenticate(user=self.invitee)

                # Wait for both threads to synchronize
                barrier.wait(timeout=10)

                # Fire accept request concurrently
                response = client.post('/api/v1/invitations/accept/', {'token': raw_token})
                results.append(response)
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)

        t1.start()
        t2.start()

        t1.join(timeout=15)
        t2.join(timeout=15)

        # Ensure no unexpected exceptions or crashes occurred in either thread
        self.assertEqual(len(errors), 0, f"Unexpected thread errors: {errors}")
        self.assertEqual(len(results), 2, "Both workers must complete")

        status_codes = sorted([r.status_code for r in results])

        # Exactly one request succeeds with 200 OK, the other is cleanly rejected with 400 Bad Request
        self.assertEqual(
            status_codes,
            [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
            f"Expected [200, 400], got {status_codes}"
        )

        # Check the 400 response body contains clean validation error, NOT an unhandled 500 IntegrityError
        losing_response = next(r for r in results if r.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', losing_response.data)

        # Verify DB state: exactly one WorkspaceMember created
        members = WorkspaceMember.objects.filter(workspace=self.workspace, user=self.invitee)
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first().role, 'member')
        self.assertEqual(members.first().status, 'active')

        # Verify invitation status ends as 'accepted'
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'accepted')
        self.assertIsNotNone(invitation.accepted_at)
