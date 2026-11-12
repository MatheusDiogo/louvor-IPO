from django.urls import path
from . import acordes_views, importacao, relatorio, views

urlpatterns = [
    # Desenhos de acordes e grafias (líderes)
    path('acordes/', acordes_views.acordes_view, name='acordes'),
    path('acordes/buscar/', acordes_views.acordes_buscar, name='acordes_buscar'),
    path('acordes/salvar/', acordes_views.acordes_salvar, name='acordes_salvar'),
    path('acordes/<int:pk>/ativo/', acordes_views.acordes_ativo, name='acordes_ativo'),
    path('acordes/<int:pk>/mover/', acordes_views.acordes_mover, name='acordes_mover'),
    path('acordes/<int:pk>/excluir/', acordes_views.acordes_excluir, name='acordes_excluir'),
    path('acordes/grafias/salvar/', acordes_views.grafia_salvar, name='grafia_salvar'),
    path('acordes/grafias/<int:pk>/excluir/', acordes_views.grafia_excluir, name='grafia_excluir'),

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
