from django.urls import path
from . import views

urlpatterns = [
    # Lista de escalas futuras
    path('', views.escala_list, name='escala_list'),

    # CRUD da escala
    path('criar/', views.escala_criar, name='escala_criar'),
    path('<int:pk>/editar/', views.escala_editar, name='escala_editar'),
    path('<int:pk>/excluir/', views.escala_excluir, name='escala_excluir'),

    # Detalhe/gerenciar músicas da escala
    path('<int:pk>/', views.escala_detalhe, name='escala_detalhe'),

    # Visualização somente leitura
    path('<int:pk>/visualizar/', views.escala_visualizar, name='escala_visualizar'),

    # Músicas na escala
    path('<int:pk>/musica/adicionar/', views.escala_musica_adicionar, name='escala_musica_adicionar'),
    path('musica/<int:item_pk>/excluir/', views.escala_musica_excluir, name='escala_musica_excluir'),

    # API AJAX
    path('api/tons/<int:musica_id>/', views.api_tons_musica, name='api_tons_musica'),
]