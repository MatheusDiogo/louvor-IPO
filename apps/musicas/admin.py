from django.contrib import admin
from .models import DesenhoAcorde, Musica, NomeAcorde


@admin.register(Musica)
class MusicaAdmin(admin.ModelAdmin):
    search_fields = ['nome']
    list_display = ('nome', 'tom', 'revisar', 'atualizado_em')
    list_filter = ('revisar',)


@admin.register(DesenhoAcorde)
class DesenhoAcordeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ordem', 'origem', 'ativo')
    list_filter = ('origem', 'ativo', 'raiz', 'tipo')
    list_editable = ('ordem', 'ativo')


@admin.register(NomeAcorde)
class NomeAcordeAdmin(admin.ModelAdmin):
    list_display = ('escrita', 'tipo', 'origem')
    list_filter = ('origem', 'tipo')
    search_fields = ('escrita', 'tipo')
