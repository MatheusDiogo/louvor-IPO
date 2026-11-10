from django import forms
from django.contrib.auth import get_user_model, password_validation

from apps.instrumentos.models import Instrumento

Usuario = get_user_model()


class CadastroForm(forms.Form):
    """Auto-cadastro de integrantes (a conta fica pendente até um líder aprovar)."""

    first_name = forms.CharField(label='Nome', max_length=150)
    last_name = forms.CharField(label='Sobrenome', max_length=150)
    email = forms.EmailField(label='E-mail')
    password1 = forms.CharField(label='Senha', widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput, strip=False)
    instrumentos = forms.ModelMultipleChoiceField(
        label='Instrumentos',
        queryset=Instrumento.objects.all(),
        required=False,
    )
    # Campo-isca: invisível para pessoas; robôs costumam preenchê-lo
    site = forms.CharField(required=False)

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        existente = Usuario.objects.filter(email__iexact=email).first()
        if existente:
            if not existente.is_active:
                raise forms.ValidationError('Este e-mail já tem um cadastro aguardando aprovação.')
            raise forms.ValidationError('Este e-mail já está cadastrado. Use "Esqueci minha senha" se não lembrar a senha.')
        return email

    def clean(self):
        dados = super().clean()
        if dados.get('site'):
            raise forms.ValidationError('Não foi possível concluir o cadastro.')

        senha1, senha2 = dados.get('password1'), dados.get('password2')
        if senha1 and senha2 and senha1 != senha2:
            self.add_error('password2', 'As senhas não coincidem.')
        elif senha1:
            usuario_temp = Usuario(
                username=dados.get('email', ''),
                email=dados.get('email', ''),
                first_name=dados.get('first_name', ''),
                last_name=dados.get('last_name', ''),
            )
            try:
                password_validation.validate_password(senha1, usuario_temp)
            except forms.ValidationError as erro:
                self.add_error('password1', erro)
        return dados

    def save(self):
        dados = self.cleaned_data
        usuario = Usuario.objects.create_user(
            username=dados['email'],
            email=dados['email'],
            password=dados['password1'],
            first_name=dados['first_name'],
            last_name=dados['last_name'],
            is_active=False,  # pendente até um líder aprovar
        )
        usuario.instrumentos.set(dados['instrumentos'])
        return usuario
