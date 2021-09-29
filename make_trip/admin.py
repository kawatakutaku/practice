from django.contrib import admin
from .models import Group, Member, Transport, Trip, Spot, Other, Budget, Memo
from django.utils.translation import ugettext_lazy as _

# Register your models here.

admin.site.register(Group)
admin.site.register(Member)
admin.site.register(Transport)
admin.site.register(Trip)
admin.site.register(Spot)
admin.site.register(Other)
admin.site.register(Budget)
admin.site.register(Memo)
