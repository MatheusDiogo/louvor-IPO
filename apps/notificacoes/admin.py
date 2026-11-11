from django.contrib import admin

from .models import InscricaoPush


@admin.register(InscricaoPush)
class InscricaoPushAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'navegador', 'atualizada_em')
    search_fields = ('usuario__first_name', 'usuario__email')
