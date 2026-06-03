from django.contrib import admin
from .models import recol_setting
from django.shortcuts import redirect
from django.urls import reverse


# Register your models here.
@admin.register(recol_setting)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ["default_ui",]

    def has_add_permission(self, request):
        return not recol_setting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        if recol_setting.objects.exists():
            obj = recol_setting.objects.first()

            url = reverse(
                "admin:recol_recol_setting_change",
                args=[obj.id]
            )
            return redirect(url)

        return super().changelist_view(request, extra_context)
    