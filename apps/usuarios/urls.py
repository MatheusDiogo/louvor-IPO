from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.integrantes_view, name='integrantes'),
    path('salvar/', views.salvar_integrante, name='salvar_integrante'),
    path('excluir/<int:id>/', views.excluir_integrante, name='excluir_integrante'),
    path('accounts/password_reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='password_reset.html',
            email_template_name='emails/password_reset_email.html',
            subject_template_name='emails/password_reset_subject.txt',
        ), 
        name='password_reset'),

    path('accounts/password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ), 
        name='password_reset_done'),

    path('accounts/reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html'
        ), 
        name='password_reset_confirm'),

    path('accounts/reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html'
        ), 
        name='password_reset_complete'),
]