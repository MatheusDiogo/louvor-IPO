from django.urls import path

from . import avisos_views, views

urlpatterns = [
    # Avisos programados (só o administrador)
    path('avisos/', avisos_views.avisos_lista, name='avisos_lista'),
    path('avisos/novo/', avisos_views.aviso_editar, name='aviso_novo'),
    path('avisos/<int:pk>/', avisos_views.aviso_editar, name='aviso_editar'),
    path('avisos/<int:pk>/excluir/', avisos_views.aviso_excluir, name='aviso_excluir'),
    path('avisos/<int:pk>/ativo/', avisos_views.aviso_ativo, name='aviso_ativo'),
    path('avisos/<int:pk>/teste/', avisos_views.aviso_enviar_teste, name='aviso_enviar_teste'),
    path('avisos/testar/', avisos_views.aviso_testar, name='aviso_testar'),

    path('inscrever/', views.inscrever, name='notificacoes_inscrever'),
    path('cancelar/', views.cancelar, name='notificacoes_cancelar'),
    path('testar/', views.testar, name='notificacoes_testar'),
]
