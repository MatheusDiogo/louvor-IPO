from django.urls import path
from . import equipe, views

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
    path('musica/<int:item_pk>/tom/', views.escala_musica_tom, name='escala_musica_tom'),
    path('<int:pk>/musicas/ordem/', views.escala_musicas_ordem, name='escala_musicas_ordem'),

    # Cifras do culto (todas no tom escolhido) e PDF do repertório
    path('<int:pk>/cifras/', views.escala_cifras, name='escala_cifras'),
    path('<int:pk>/pdf/', views.escala_pdf, name='escala_pdf'),

    # Escala de integrantes (somente líderes)
    path('equipe/', equipe.escala_equipe, name='escala_equipe'),
    path('equipe/data/', equipe.escala_equipe_adicionar_data, name='escala_equipe_adicionar_data'),
    path('equipe/salvar/', equipe.escala_equipe_salvar, name='escala_equipe_salvar'),
    path('equipe/publicar/', equipe.escala_equipe_publicar, name='escala_equipe_publicar'),
    path('equipe/exportar/', equipe.escala_equipe_exportar, name='escala_equipe_exportar'),

]