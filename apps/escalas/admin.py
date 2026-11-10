from django.contrib import admin
from .models import Escala, EscalaMusica, EscalaIntegrante


class EscalaMusicaInline(admin.TabularInline):
    model = EscalaMusica
    extra = 1
    autocomplete_fields = ['musica']


class EscalaIntegranteInline(admin.TabularInline):
    model = EscalaIntegrante
    extra = 1


@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    list_display = ('data', 'ministrante', 'observacao')
    inlines = [EscalaIntegranteInline, EscalaMusicaInline]
