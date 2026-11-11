from django.urls import path

from . import views

urlpatterns = [
    path('inscrever/', views.inscrever, name='notificacoes_inscrever'),
    path('cancelar/', views.cancelar, name='notificacoes_cancelar'),
    path('testar/', views.testar, name='notificacoes_testar'),
]
