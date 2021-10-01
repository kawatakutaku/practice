from django.db import models
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.core.validators import MinLengthValidator, MinValueValidator
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _
from accounts.models import CustomUser


# Create your models here.
class Group(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='trip_user')
    title = models.CharField(max_length=30)

    def __str__(self):
        return '<' + self.title + '(' + str(self.user) + ')>'

class Member(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='member_user')
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