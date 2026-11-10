from django.urls import path
from . import importacao, relatorio, views

urlpatterns = [
    path('', views.musicas_view, name='musicas'),
    path('nova/', views.musica_editar, name='musica_nova'),
    path('<int:musica_id>/', views.detalhes_musica, name='detalhes_musica'),
    path('<int:musica_id>/editar/', views.musica_editar, name='musica_editar'),
    path('<int:musica_id>/pdf/', views.musica_pdf, name='musica_pdf'),
    path('excluir/<int:id>/', views.excluir_musica, name='excluir_musica'),
    path('previa/', views.musica_previa, name='musica_previa'),
    path('converter/', views.musica_converter, name='musica_converter'),
    path('relatorio/', relatorio.relatorio_musicas, name='relatorio_musicas'),

    # Importação do caderno de cifras em PDF
    path('importar/', importacao.importar_pdf, name='importar_pdf'),
    path('importar/confirmar/', importacao.importar_pdf_confirmar, name='importar_pdf_confirmar'),
    path('importar/<str:token>/<int:numero>/', importacao.importar_pdf_previa, name='importar_pdf_previa'),
]
