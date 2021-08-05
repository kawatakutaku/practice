from django.contrib import admin
from .models import Group, Member, Transport, Trip, Spot, Other, User, Budget, Memo
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import ugettext_lazy as _

# Register your models here.

class MyCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', )

class MyChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'username')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    form = MyChangeForm
    add_form = MyCreationForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('email',)

admin.site.register(User, MyUserAdmin)
admin.site.register(Group)
admin.site.register(Member)
admin.site.register(Transport)
admin.site.register(Trip)
admin.site.register(Spot)
admin.site.register(Other)
admin.site.register(Budget)
admin.site.register(Memo)
