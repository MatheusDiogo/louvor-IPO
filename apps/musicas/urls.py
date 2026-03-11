from django.urls import path
from . import views

urlpatterns = [
    path('', views.musicas_view, name='musicas'),
    path('<int:musica_id>/', views.detalhes_musica, name='detalhes_musica'),
    path('salvar/', views.salvar_musica, name='salvar_musica'),
    path('excluir/<int:id>/', views.excluir_musica, name='excluir_musica'),
    path('tom/salvar/', views.salvar_tom, name='salvar_tom'),
    path('tom/excluir/<int:id>/', views.excluir_tom, name='excluir_tom'),
]