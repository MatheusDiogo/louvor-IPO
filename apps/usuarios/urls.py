from django.urls import path
from . import views

urlpatterns = [
    path('', views.integrantes_view, name='integrantes'),
    path('salvar/', views.salvar_integrante, name='salvar_integrante'),
    path('excluir/<int:id>/', views.excluir_integrante, name='excluir_integrante'),
]