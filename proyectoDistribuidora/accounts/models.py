import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

from .managers import DistributorManager, NotificationQuerySet


class Role(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Súper Admin'
    DISTRIBUTOR = "DISTRIBUTOR", "Distribuidor"
    STORE_OWNER = "STORE_OWNER", "Dueño de Tienda"
    VENDOR = "VENDOR", "Vendedor"
    DELIVERY = "DELIVERY", "Repartidor"


class TenantStatus(models.TextChoices):
    ACTIVE    = 'ACTIVE',    'Activo'
    SUSPENDED = 'SUSPENDED', 'Suspendido'
    TRIAL     = 'TRIAL',     'Prueba'
    CANCELLED = 'CANCELLED', 'Cancelado'


class TenantPlan(models.TextChoices):
    FREE     = 'FREE',     'Gratis'
    STANDARD = 'STANDARD', 'Estándar'
    PREMIUM  = 'PREMIUM',  'Premium'


class Distributor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    status = models.CharField(max_length=20, choices=TenantStatus.choices, default=TenantStatus.ACTIVE)
    plan   = models.CharField(max_length=20, choices=TenantPlan.choices, default=TenantPlan.FREE)

    # Opaque per-distributor invite token: powers the STORE_OWNER
    # self-registration link/QR code. Deliberately not a public distributor
    # picker — the token itself implies which distributor a new store owner
    # is joining, so the list of distributors is never exposed.
    invite_token = models.CharField(max_length=64, unique=True, editable=False)

    objects = DistributorManager()

    def save(self, *args, **kwargs):
        if not self.invite_token:
            self.invite_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def regenerate_invite_token(self):
        """Revoke the current invite link (e.g. after it leaks) and issue a new one."""
        self.invite_token = secrets.token_urlsafe(32)
        self.save(update_fields=['invite_token'])

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def for_distributor(self, distributor):
        return self.filter(distributor=distributor)

    def vendors_for(self, distributor):
        return self.filter(distributor=distributor, role=Role.VENDOR)


class User(AbstractUser):
    # username is kept from AbstractUser but made optional since we log in with email
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True
    )

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email is already USERNAME_FIELD, no extra required fields

    objects = UserManager()

    def __str__(self):
        return self.email


class DistributorInvitation(models.Model):
    """Single-use, expiring invitation token letting a prospective distributor
    self-register (accounts/views.py:registrar_distribuidor), instead of a
    superuser creating the Distributor+admin manually via crear_distribuidor.
    Extends PasswordResetToken's expiry/single-use shape with created_by and
    revoked_at — not a field-for-field mirror.

    Redemption concurrency: registrar_distribuidor must open ONE
    transaction.atomic() with select_for_update() on this row that also
    contains the Distributor+User creation and the used_at write — never a
    separate transaction for creation, or the lock stops protecting against
    double-redemption. See docs/TODOS.md Tier 6 item 3 for the full reasoning
    (mirrors orders.views.aceptar_pedido's single-atomic-block lock pattern).
    """

    token = models.CharField(max_length=255, unique=True, editable=False)

    # The prospective admin user's email (matched at redemption), NOT the
    # distributor's company email. Blank means link-only: anyone with the
    # link can redeem it under any email.
    target_email = models.EmailField(blank=True)

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(null=True, blank=True)

    revoked_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="issued_invitations",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def is_usable(self):
        return self.used_at is None and self.revoked_at is None and not self.is_expired()

    def unusable_reason(self):
        """The user-facing reason this invitation can't be redeemed, or None if
        it's still usable — drives the friendly GET-time rejection page."""
        if self.revoked_at is not None:
            return 'esta invitación fue revocada'
        if self.used_at is not None:
            return 'este enlace ya fue utilizado'
        if self.is_expired():
            return 'el enlace ha expirado, solicita uno nuevo'
        return None

    def __str__(self):
        return f"Invitation {self.token[:8]}... ({self.target_email or 'link-only'})"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )

    token = models.CharField(max_length=255, unique=True)

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def is_usable(self):
        return self.used_at is None and not self.is_expired()

    def unusable_reason(self):
        """The user-facing reason this reset link can't be used, or None."""
        if self.used_at is not None:
            return 'este enlace ya fue utilizado'
        if self.is_expired():
            return 'el enlace ha expirado, solicita uno nuevo'
        return None

    def __str__(self):
        return self.token


class NotificationPreference(models.Model):
    """Per-user notification + alert preferences, created lazily via
    `for_user()` (get_or_create). Every default preserves today's always-on
    behavior, so existing users see no change until they opt out from the
    Configuración page."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )

    # In-app Notification gating (Order._notify / low-stock digest).
    order_updates = models.BooleanField(default=True)      # order status-change notifications
    low_stock_alerts = models.BooleanField(default=True)   # distributor low-stock digest

    # VENDOR new-order polling (orders/templates/orders/index.html).
    new_order_alerts = models.BooleanField(default=True)   # poll + surface new pending orders
    poll_interval_seconds = models.PositiveIntegerField(default=30)  # cadence; form clamps to >=10

    def wants(self, category):
        """Whether the user opted in to a notification category (default True
        for unknown categories so a new event type never goes silent by
        accident)."""
        return {
            "order_updates": self.order_updates,
            "low_stock_alerts": self.low_stock_alerts,
            "new_order_alerts": self.new_order_alerts,
        }.get(category, True)

    @classmethod
    def for_user(cls, user):
        pref, _ = cls.objects.get_or_create(user=user)
        return pref

    def __str__(self):
        return f"Preferencias de {self.user}"


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    # String FK avoids circular import with the orders app
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    message = models.CharField(max_length=500)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.message[:50]}"