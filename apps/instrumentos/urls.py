from django.urls import path
from . import views

urlpatterns = [

    path("", views.instrumentos_view, name="instrumentos"),

    path("salvar/", views.salvar_instrumento, name="salvar_instrumento"),

    path("excluir/<int:id>/", views.excluir_instrumento, name="excluir_instrumento"),
]