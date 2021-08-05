from django.db import models
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.core.validators import MinLengthValidator, MinValueValidator
from django.utils import timezone
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _


class CustomUserManager(UserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError('メールアドレスを入力してください')
        if not username:
            raise ValueError('ユーザーネームを入力してください')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, email, username, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):

    username = models.CharField( _('username'), max_length=150)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = CustomUserManager()

    EMAIL_FIELD = 'username'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


# Create your models here.
class Group(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trip_user')
    title = models.CharField(max_length=30)

    def __str__(self):
        return '<' + self.title + '(' + str(self.user) + ')>'

class Member(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='member_user')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='member_group')

    def __str__(self):
        return str(self.user) + ' (group:" ' + str(self.group) + ' " )'

class Trip(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='trip_group')
    trip_name = models.CharField(max_length=30)
    start = models.DateField()
    end = models.DateField()

    def __str__(self):
        return str(self.trip_name) + ' (' + str(self.group) + ',' + str(self.start)  + '〜' + str(self.end) + ')'

class Spot(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='spot')
    spot_name = models.CharField(max_length=50)
    spot_time = models.DateTimeField()
    spot_cost = models.IntegerField(validators=[MinValueValidator(0, '0以上で入力してください')])

    def __str__(self):
        return str(self.spot_name) + ' (' + str(self.spot_time) + '+' + str(self.spot_cost) + ')'

class Other(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='extra')
    extra_name = models.CharField(max_length=50)
    extra_cost = models.IntegerField(validators=[MinValueValidator(0, '0以上で入力してください')])

    def __str__(self):
        return str(self.extra_name) + ' (' + str(self.extra_cost) + ')'

class Transport(models.Model):
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE, related_name='transport_spot')
    transport_name = models.CharField(max_length=30)
    transport_fee = models.IntegerField(validators=[MinValueValidator(0, '0以上で入力してください')])
    transport_time = models.DateTimeField()

    def __str__(self):
        return str(self.transport_name) + ': ' + str(self.transport_time) + ' (' + str(self.transport_fee) + ')'

class Budget(models.Model):
    predict_money = models.IntegerField(validators=[MinValueValidator(0, '0以上で入力してください')])
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='budget')

    def __str__(self):
        return str(self.predict_money)

class Memo(models.Model):
    memo = models.TextField(blank=True, null=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='trip_memo')

    def __str__(self):
        return str(self.memo)

'''
class Cost(models.Model):
    cost_name = models.CharField(max_length=30)
    cost_money = models.IntegerField(validators=[MinValueValidator(0, '0以上で入力してください')])
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE, related_name='spot_cost')

    def __str__(self):
        return str(self.cost_name) + '(' + str(self.cost_money) + ')'
'''