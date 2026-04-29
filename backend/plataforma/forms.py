from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Tecnico, Proveedor


class RegistroTecnicoForm(UserCreationForm):
    """Formulario de registro para técnicos"""
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    email = forms.EmailField(required=True)
    cuit = forms.CharField(max_length=13, required=True, label="CUIT (XX-XXXXXXXX-X)")
    especialidad = forms.CharField(max_length=100, required=True, label="Especialidad")
    ubicacion = forms.CharField(max_length=200, required=True, label="Ubicación")

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'cuit', 'especialidad', 'ubicacion', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        return email

    def clean_cuit(self):
        cuit = self.cleaned_data.get('cuit')
        if Tecnico.objects.filter(cuit=cuit).exists():
            raise forms.ValidationError("Este CUIT ya está registrado.")
        return cuit

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.is_active = False

        if commit:
            user.save()
            Tecnico.objects.create(
                usuario=user,
                cuit=self.cleaned_data['cuit'],
                especialidad=self.cleaned_data['especialidad'],
                ubicacion=self.cleaned_data['ubicacion'],
                is_approved=False
            )
        return user


class RegistroProveedorForm(UserCreationForm):
    """Formulario de registro para proveedores"""
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    email = forms.EmailField(required=True)
    cuit = forms.CharField(max_length=13, required=True, label="CUIT (XX-XXXXXXXX-X)")
    nombre_negocio = forms.CharField(max_length=150, required=True, label="Nombre del Negocio")
    direccion = forms.CharField(max_length=255, required=True, label="Dirección")
    rubro = forms.CharField(max_length=100, required=True, label="Rubro")

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'cuit', 'nombre_negocio', 'direccion', 'rubro', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        return email

    def clean_cuit(self):
        cuit = self.cleaned_data.get('cuit')
        if Proveedor.objects.filter(cuit=cuit).exists():
            raise forms.ValidationError("Este CUIT ya está registrado.")
        return cuit

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.is_active = False

        if commit:
            user.save()
            Proveedor.objects.create(
                usuario=user,
                cuit=self.cleaned_data['cuit'],
                nombre_negocio=self.cleaned_data['nombre_negocio'],
                direccion=self.cleaned_data['direccion'],
                rubro=self.cleaned_data['rubro'],
                is_approved=False
            )
        return user


class LoginForm(forms.Form):
    """Formulario de login con email"""
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput(), label="Contraseña")
