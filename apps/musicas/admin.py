from django.contrib import admin
from .models import Musica


@admin.register(Musica)
class MusicaAdmin(admin.ModelAdmin):
    search_fields = ['nome']
    list_display = ('nome', 'tom', 'revisar', 'atualizado_em')
    list_filter = ('revisar',)
