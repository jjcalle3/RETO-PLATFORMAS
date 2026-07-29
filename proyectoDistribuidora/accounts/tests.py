import threading
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.db import OperationalError, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from .models import Distributor, DistributorInvitation, Notification, NotificationPreference, Role, User


def make_superuser(email='super@test.com'):
    return User.objects.create_superuser(email=email, password='pass1234')


def make_invitation(target_email='', days_valid=7, created_by=None):
    import secrets
    return DistributorInvitation.objects.create(
        token=secrets.token_urlsafe(32),
        target_email=target_email,
        expires_at=timezone.now() + timedelta(days=days_valid),
        created_by=created_by,
    )


class DistributorInvitationModelTest(TestCase):
    def test_token_unique(self):
        superuser = make_superuser()
        inv1 = make_invitation(created_by=superuser)
        with self.assertRaises(Exception):
            DistributorInvitation.objects.create(
                token=inv1.token, expires_at=timezone.now() + timedelta(days=7)
            )

    def test_is_usable_true_for_fresh_invitation(self):
        inv = make_invitation()
        self.assertTrue(inv.is_usable())
        self.assertFalse(inv.is_expired())

    def test_is_usable_false_when_expired(self):
        inv = make_invitation(days_valid=-1)
        self.assertTrue(inv.is_expired())
        self.assertFalse(inv.is_usable())

    def test_is_usable_false_when_used(self):
        inv = make_invitation()
        inv.used_at = timezone.now()
        inv.save(update_fields=['used_at'])
        self.assertFalse(inv.is_usable())

    def test_is_usable_false_when_revoked(self):
        inv = make_invitation()
        inv.revoked_at = timezone.now()
        inv.save(update_fields=['revoked_at'])
        self.assertFalse(inv.is_usable())

    def test_created_by_set_null_on_delete(self):
        superuser = make_superuser()
        inv = make_invitation(created_by=superuser)
        superuser.delete()
        inv.refresh_from_db()
        self.assertIsNone(inv.created_by)


class EmitirInvitacionViewTest(TestCase):
    def setUp(self):
        self.superuser = make_superuser()
        self.client = Client()

    def test_get_renders_form(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('emitir_invitacion'))
        self.assertEqual(response.status_code, 200)

    def test_non_superuser_forbidden(self):
        distribuidor = Distributor.objects.create(name='D1', email='d1@test.com')
        normal_user = User.objects.create_user(
            email='u@test.com', password='pass1234', role=Role.DISTRIBUTOR, distributor=distribuidor
        )
        self.client.force_login(normal_user)
        response = self.client.get(reverse('emitir_invitacion'))
        self.assertEqual(response.status_code, 403)

    def test_post_with_target_email_sends_mail(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('emitir_invitacion'), {'target_email': 'prospect@test.com'})
        self.assertEqual(response.status_code, 302)
        inv = DistributorInvitation.objects.get(target_email='prospect@test.com')
        self.assertEqual(inv.created_by, self.superuser)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('prospect@test.com', mail.outbox[0].to)
        self.assertTrue(
            AuditLog.objects.filter(action='invitation_issued', entity_id=str(inv.id)).exists()
        )

    def test_post_blank_target_email_does_not_send_mail(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('emitir_invitacion'), {'target_email': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        inv = DistributorInvitation.objects.get(target_email='')
        self.assertIsNotNone(inv)

    def test_post_email_send_failure_does_not_lose_invitation(self):
        self.client.force_login(self.superuser)
        with patch('accounts.views.send_mail', side_effect=Exception('SMTP down')):
            response = self.client.post(
                reverse('emitir_invitacion'), {'target_email': 'prospect@test.com'}
            )
        self.assertEqual(response.status_code, 302)
        # Invitation persists even though the email send raised.
        self.assertTrue(DistributorInvitation.objects.filter(target_email='prospect@test.com').exists())


class InvitacionesListViewTest(TestCase):
    def setUp(self):
        self.superuser = make_superuser()
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_empty_state(self):
        response = self.client.get(reverse('invitaciones'))
        self.assertContains(response, 'No hay invitaciones pendientes')

    def test_lists_invitations_by_state(self):
        pendiente = make_invitation(target_email='pending@test.com', created_by=self.superuser)
        usada = make_invitation(target_email='used@test.com', created_by=self.superuser)
        usada.used_at = timezone.now()
        usada.save(update_fields=['used_at'])
        expirada = make_invitation(target_email='expired@test.com', days_valid=-1, created_by=self.superuser)
        revocada = make_invitation(target_email='revoked@test.com', created_by=self.superuser)
        revocada.revoked_at = timezone.now()
        revocada.save(update_fields=['revoked_at'])

        response = self.client.get(reverse('invitaciones'))
        self.assertContains(response, 'pending@test.com')
        self.assertContains(response, 'used@test.com')
        self.assertContains(response, 'expired@test.com')
        self.assertContains(response, 'revoked@test.com')

    def test_non_superuser_forbidden(self):
        distribuidor = Distributor.objects.create(name='D1', email='d1@test.com')
        normal_user = User.objects.create_user(
            email='u@test.com', password='pass1234', role=Role.DISTRIBUTOR, distributor=distribuidor
        )
        client = Client()
        client.force_login(normal_user)
        response = client.get(reverse('invitaciones'))
        self.assertEqual(response.status_code, 403)


class RevocarInvitacionViewTest(TestCase):
    def setUp(self):
        self.superuser = make_superuser()
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_revoke_blocks_later_redemption(self):
        inv = make_invitation(created_by=self.superuser)
        self.client.post(reverse('revocar_invitacion', args=[inv.id]))
        inv.refresh_from_db()
        self.assertIsNotNone(inv.revoked_at)
        self.assertTrue(
            AuditLog.objects.filter(action='invitation_revoked', entity_id=str(inv.id)).exists()
        )

        response = self.client.get(reverse('registrar_distribuidor', args=[inv.token]))
        self.assertContains(response, 'revocada')

    def test_revoke_already_used_is_safe_noop(self):
        inv = make_invitation(created_by=self.superuser)
        inv.used_at = timezone.now()
        inv.save(update_fields=['used_at'])
        response = self.client.post(reverse('revocar_invitacion', args=[inv.id]))
        self.assertEqual(response.status_code, 302)
        inv.refresh_from_db()
        # Idempotent — revoking an already-used token doesn't error, and it
        # still shows as "used" (used_at check comes first at redemption).
        self.assertIsNotNone(inv.used_at)


class RegistrarDistribuidorViewTest(TestCase):
    def setUp(self):
        self.superuser = make_superuser()
        self.client = Client()

    def _join_payload(self, **overrides):
        payload = {
            'distributor_name': 'Nueva Distribuidora',
            'distributor_email': 'nueva@test.com',
            'admin_email': 'admin@nueva.com',
            'admin_password1': 'ContraseñaSegura123',
            'admin_password2': 'ContraseñaSegura123',
        }
        payload.update(overrides)
        return payload

    def test_token_not_found_404(self):
        response = self.client.get(reverse('registrar_distribuidor', args=['bogus-token']))
        self.assertEqual(response.status_code, 404)

    def test_expired_token_shows_distinct_message(self):
        inv = make_invitation(days_valid=-1, created_by=self.superuser)
        response = self.client.get(reverse('registrar_distribuidor', args=[inv.token]))
        self.assertContains(response, 'expirado')

    def test_used_token_shows_distinct_message(self):
        inv = make_invitation(created_by=self.superuser)
        inv.used_at = timezone.now()
        inv.save(update_fields=['used_at'])
        response = self.client.get(reverse('registrar_distribuidor', args=[inv.token]))
        self.assertContains(response, 'utilizado')

    def test_revoked_token_shows_distinct_message(self):
        inv = make_invitation(created_by=self.superuser)
        inv.revoked_at = timezone.now()
        inv.save(update_fields=['revoked_at'])
        response = self.client.get(reverse('registrar_distribuidor', args=[inv.token]))
        self.assertContains(response, 'revocada')

    def test_email_mismatch_rejected(self):
        inv = make_invitation(target_email='expected@test.com', created_by=self.superuser)
        response = self.client.post(
            reverse('registrar_distribuidor', args=[inv.token]),
            self._join_payload(admin_email='someoneelse@test.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no coincide')
        inv.refresh_from_db()
        self.assertIsNone(inv.used_at)

    def test_email_match_case_insensitive_succeeds(self):
        inv = make_invitation(target_email='expected@test.com', created_by=self.superuser)
        response = self.client.post(
            reverse('registrar_distribuidor', args=[inv.token]),
            self._join_payload(admin_email='EXPECTED@test.com'),
        )
        self.assertEqual(response.status_code, 302)

    def test_valid_redemption_creates_distributor_and_user_and_logs_in(self):
        inv = make_invitation(created_by=self.superuser)
        response = self.client.post(
            reverse('registrar_distribuidor', args=[inv.token]), self._join_payload()
        )
        self.assertEqual(response.status_code, 302)

        distribuidor = Distributor.objects.get(email='nueva@test.com')
        admin = User.objects.get(email='admin@nueva.com')
        self.assertEqual(admin.role, Role.DISTRIBUTOR)
        self.assertEqual(admin.distributor, distribuidor)

        inv.refresh_from_db()
        self.assertIsNotNone(inv.used_at)

        log = AuditLog.objects.get(action='invitation_redeemed', entity_id=str(inv.id))
        self.assertEqual(log.user, admin)

        # Auto-login: the session now belongs to the new admin.
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_duplicate_admin_email_rejected_by_form(self):
        User.objects.create_user(email='admin@nueva.com', password='x', role=Role.DISTRIBUTOR)
        inv = make_invitation(created_by=self.superuser)
        response = self.client.post(
            reverse('registrar_distribuidor', args=[inv.token]), self._join_payload()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe un usuario con este correo')
        inv.refresh_from_db()
        self.assertIsNone(inv.used_at)


class RegistrarDistribuidorConcurrencyTest(TransactionTestCase):
    """Genuine multi-threaded regression for the select_for_update() lock —
    mirrors orders.tests.OrderAcceptConcurrencyTest exactly (Eng-Review
    Finding B2). SQLite serializes writers at the database-file level (no
    true row-level concurrency), so this proves "no double-redeem", not
    "both threads ran in true parallel" — the latter needs Postgres. A
    thread that hits OperationalError (database is locked) is treated as a
    losing thread, not a failure, since that's SQLite's own serialization
    mechanism."""

    def test_concurrent_redemptions_exactly_one_succeeds(self):
        import secrets
        superuser = User.objects.create_superuser(email='super2@test.com', password='pass1234')
        token = secrets.token_urlsafe(32)
        invitation = DistributorInvitation.objects.create(
            token=token, expires_at=timezone.now() + timedelta(days=7), created_by=superuser
        )

        def redeem(suffix):
            try:
                client = Client()
                client.post(
                    reverse('registrar_distribuidor', args=[token]),
                    {
                        'distributor_name': f'Distribuidora {suffix}',
                        'distributor_email': f'dist{suffix}@test.com',
                        'admin_email': f'admin{suffix}@test.com',
                        'admin_password1': 'ContraseñaSegura123',
                        'admin_password2': 'ContraseñaSegura123',
                    },
                )
            except OperationalError:
                pass  # SQLite lock contention — this thread loses, not a failure
            finally:
                connection.close()

        threads = [threading.Thread(target=redeem, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(Distributor.objects.filter(name__startswith='Distribuidora').count(), 1)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.used_at)


class CrearDistribuidorRedirectRegressionTest(TestCase):
    """Regression test for Eng-Review Finding A1: crear_distribuidor's
    success redirect used to send the superuser into a 403 wall
    (redirect(index), and index is @role_required('DISTRIBUTOR'))."""

    def test_success_redirects_to_invitations_not_403(self):
        superuser = make_superuser()
        client = Client()
        client.force_login(superuser)
        response = client.post(reverse('crear_distribuidor'), {
            'distributor_name': 'Otra Distribuidora',
            'distributor_email': 'otra@test.com',
            'admin_email': 'admin@otra.com',
            'admin_password1': 'ContraseñaSegura123',
            'admin_password2': 'ContraseñaSegura123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.redirect_chain[-1][1], 403)


class DistributorManagerTest(TestCase):
    def test_status_counts_tallies_by_status(self):
        from .models import TenantStatus
        Distributor.objects.create(name='A', email='a@t.com', status=TenantStatus.ACTIVE)
        Distributor.objects.create(name='B', email='b@t.com', status=TenantStatus.ACTIVE)
        Distributor.objects.create(name='C', email='c@t.com', status=TenantStatus.SUSPENDED)
        totales = Distributor.objects.status_counts()
        self.assertEqual(totales[TenantStatus.ACTIVE], 2)
        self.assertEqual(totales[TenantStatus.SUSPENDED], 1)
        self.assertEqual(totales[TenantStatus.CANCELLED], 0)

    def test_create_with_admin_creates_both(self):
        from .models import Role
        distribuidor, admin = Distributor.objects.create_with_admin(
            name='Nueva', email='nueva@t.com',
            admin_email='admin@nueva.com', admin_password='pass1234',
        )
        self.assertEqual(admin.role, Role.DISTRIBUTOR)
        self.assertEqual(admin.distributor, distribuidor)
        self.assertTrue(admin.check_password('pass1234'))


class NotificationManagerTest(TestCase):
    def setUp(self):
        self.distributor = Distributor.objects.create(name='D', email='d@t.com')
        self.user = User.objects.create_user(
            email='u@t.com', password='x', role=Role.DISTRIBUTOR, distributor=self.distributor
        )

    def _notif(self, is_read=False):
        from .models import Notification
        return Notification.objects.create(user=self.user, message='hola', is_read=is_read)

    def test_unread_read_split(self):
        self._notif(is_read=False)
        self._notif(is_read=True)
        self.assertEqual(self.user.notifications.unread().count(), 1)
        self.assertEqual(self.user.notifications.read().count(), 1)

    def test_mark_all_read(self):
        self._notif(is_read=False)
        self._notif(is_read=False)
        self.user.notifications.mark_all_read()
        self.assertEqual(self.user.notifications.unread().count(), 0)


class PasswordResetTokenUsableTest(TestCase):
    def _token(self, hours):
        from .models import PasswordResetToken
        distributor = Distributor.objects.create(name='D', email='d@t.com')
        user = User.objects.create_user(email='u@t.com', password='x', distributor=distributor)
        return PasswordResetToken.objects.create(
            user=user, token='tok', expires_at=timezone.now() + timedelta(hours=hours)
        )

    def test_fresh_token_usable(self):
        token = self._token(1)
        self.assertTrue(token.is_usable())
        self.assertIsNone(token.unusable_reason())

    def test_expired_token_unusable(self):
        token = self._token(-1)
        self.assertFalse(token.is_usable())
        self.assertIn('expirado', token.unusable_reason())

    def test_used_token_unusable(self):
        token = self._token(1)
        token.used_at = timezone.now()
        token.save()
        self.assertFalse(token.is_usable())
        self.assertIn('utilizado', token.unusable_reason())


class ConfigMenuTest(TestCase):
    """Self-service Configuración hub — RBAC, self-scoping, and the two
    landmines flagged in the CEO review (privilege-widening via reused forms;
    silent logout after password change)."""

    def setUp(self):
        self.distributor = Distributor.objects.create(name='D', email='d@test.com')
        self.owner = User.objects.create_user(
            email='owner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=self.distributor
        )
        self.vendor = User.objects.create_user(
            email='vendor@test.com', password='pass1234', role=Role.VENDOR, distributor=self.distributor
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass1234', role=Role.DISTRIBUTOR, distributor=self.distributor
        )
        self.url = reverse('configuracion')

    def _login(self, user):
        client = Client()
        client.force_login(user)
        return client

    def test_requires_login(self):
        response = Client().get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_renders_for_each_role(self):
        for user in (self.owner, self.vendor, self.admin):
            response = self._login(user).get(self.url)
            self.assertEqual(response.status_code, 200, f'{user.role} got {response.status_code}')

    def test_edit_own_name_no_id_needed(self):
        client = self._login(self.owner)
        response = client.post(self.url, {'section': 'perfil', 'username': 'Doña Rosa'})
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.username, 'Doña Rosa')

    def test_change_password_wrong_current_rejected(self):
        client = self._login(self.owner)
        response = client.post(self.url, {
            'section': 'password',
            'old_password': 'WRONG',
            'new_password1': 'NuevaClave987',
            'new_password2': 'NuevaClave987',
        })
        self.assertEqual(response.status_code, 200)  # re-render with error
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password('pass1234'))  # unchanged

    def test_change_password_success_keeps_session(self):
        client = self._login(self.owner)
        response = client.post(self.url, {
            'section': 'password',
            'old_password': 'pass1234',
            'new_password1': 'NuevaClave987',
            'new_password2': 'NuevaClave987',
        })
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password('NuevaClave987'))
        # Session survived the hash rotation — still authenticated, not bounced to login.
        self.assertEqual(client.get(self.url).status_code, 200)
        # Security tamper-evidence notification fired.
        self.assertTrue(Notification.objects.filter(user=self.owner, message__icontains='contraseña').exists())

    def test_notif_pref_gates_order_notification(self):
        from orders.models import Order, OrderStatus
        from catalog.models import Store
        store = Store.objects.create(name='T', distributor=self.distributor, owner=self.owner, vendor=self.vendor)
        order = Order.objects.create(store=store, vendor=self.vendor, status=OrderStatus.PENDING)
        pref = NotificationPreference.for_user(self.owner)
        pref.order_updates = False
        pref.save()
        order._notify(self.owner, 'algo pasó')
        self.assertEqual(Notification.objects.filter(user=self.owner).count(), 0)
        pref.order_updates = True
        pref.save()
        order._notify(self.owner, 'algo pasó')
        self.assertEqual(Notification.objects.filter(user=self.owner).count(), 1)

    def test_distributor_self_edit_cannot_escalate_status(self):
        from .forms import DistributorSelfEditForm
        # The form must not even expose status/plan/invite_token.
        self.assertNotIn('status', DistributorSelfEditForm().fields)
        self.assertNotIn('plan', DistributorSelfEditForm().fields)
        self.assertNotIn('invite_token', DistributorSelfEditForm().fields)
        # On an ACTIVE tenant, a crafted status/plan in the POST is ignored;
        # only name/email are writable. (A SUSPENDED tenant can't reach here at
        # all — suspension is enforced app-wide by middleware.)
        client = self._login(self.admin)
        response = client.post(self.url, {
            'section': 'negocio', 'name': 'Nuevo Nombre', 'email': 'd@test.com',
            'status': 'SUSPENDED', 'plan': 'PREMIUM',
        })
        self.assertEqual(response.status_code, 302)
        self.distributor.refresh_from_db()
        self.assertEqual(self.distributor.name, 'Nuevo Nombre')  # writable
        self.assertEqual(self.distributor.status, 'ACTIVE')      # crafted status ignored
        self.assertEqual(self.distributor.plan, 'FREE')          # crafted plan ignored

    def test_vendor_poll_interval_minimum(self):
        from .forms import VendorAlertPrefsForm
        pref = NotificationPreference.for_user(self.vendor)
        self.assertFalse(VendorAlertPrefsForm({'new_order_alerts': True, 'poll_interval_seconds': 5}, instance=pref).is_valid())
        self.assertTrue(VendorAlertPrefsForm({'new_order_alerts': True, 'poll_interval_seconds': 15}, instance=pref).is_valid())
