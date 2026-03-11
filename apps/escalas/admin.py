from django.contrib import admin
from .models import Escala, EscalaMusica

class EscalaMusicaInline(admin.TabularInline):
    model = EscalaMusica
    extra = 1
    autocomplete_fields = ['musica', 'tom']

@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    list_display = ('data', 'observacao')
    inlines = [EscalaMusicaInline]