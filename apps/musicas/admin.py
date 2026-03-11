from django.contrib import admin
from .models import Musica, Tom

@admin.register(Musica)
class MusicaAdmin(admin.ModelAdmin):
    # Isso permite que a música seja pesquisada em outros formulários
    search_fields = ['nome'] 
    list_display = ('nome',)

@admin.register(Tom)
class TomAdmin(admin.ModelAdmin):
    search_fields = ['tom']
    list_display = ('tom',)