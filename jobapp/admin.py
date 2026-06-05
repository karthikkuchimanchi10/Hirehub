from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Users
# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Users

@admin.register(Users)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'UserRole',
        'is_approved', 'is_staff', 'is_active'
    )
    list_filter = ('UserRole', 'is_approved', 'is_staff', 'is_active')

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'Gender', 'DOB', 'Mobile_num')
        }),
        ('Employment Info', {
            'fields': ('UserRole', 
                       'company_name', 'company_mail')
        }),
        ('Approval', {
            'fields': ('is_approved',)
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
    )

    # 👇 Here we include ALL fields for user creation
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2',
                'first_name', 'last_name', 'email',
                'Gender', 'DOB', 'Mobile_num',
                'UserRole',
                'company_name', 'company_mail',
                'is_approved', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions'
            ),
        }),
    )

    search_fields = ('username', 'email', 'UserRole')
    ordering = ('username',)
