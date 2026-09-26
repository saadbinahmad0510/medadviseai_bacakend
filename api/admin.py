from django.contrib import admin

from .models import Consultation, Profile


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'grade', 'confidence', 'created_at']


admin.site.register(Profile)
