from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .choices import RUBROS_CHOICES
from .models import Proveedor, Tecnico


class RegistroTecnicoForm(UserCreationForm):
    """Formulario de registro para técnicos"""
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    email = forms.EmailField(required=True)
    cuit = forms.CharField(max_length=13, required=True, label="CUIT (XX-XXXXXXXX-X)")
    especialidad = forms.ChoiceField(choices=RUBROS_CHOICES, required=True, label="Especialidad")
    latitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")
    ubicacion = forms.CharField(max_length=200, required=True, label="Ubicación")

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'cuit', 'especialidad', 'telefono',
            'ubicacion', 'latitud', 'longitud', 'password1', 'password2',
        )

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
                telefono=self.cleaned_data.get('telefono', ''),
                ubicacion=self.cleaned_data['ubicacion'],
                latitud=self.cleaned_data.get('latitud'),
                longitud=self.cleaned_data.get('longitud'),
                is_approved=False,
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
    rubro = forms.ChoiceField(choices=RUBROS_CHOICES, required=True, label="Rubro")
    latitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    horario_desde = forms.IntegerField(
        min_value=0, max_value=23, required=False, label="Desde (hs)",
        widget=forms.NumberInput(attrs={'min': 0, 'max': 23, 'placeholder': 'Ej: 9'}),
    )
    horario_hasta = forms.IntegerField(
        min_value=0, max_value=23, required=False, label="Hasta (hs)",
        widget=forms.NumberInput(attrs={'min': 0, 'max': 23, 'placeholder': 'Ej: 18'}),
    )

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'cuit', 'nombre_negocio',
            'direccion', 'latitud', 'longitud', 'rubro', 'horario_desde',
            'horario_hasta', 'password1', 'password2',
        )

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
            desde = self.cleaned_data.get('horario_desde')
            hasta = self.cleaned_data.get('horario_hasta')
            horarios = f"{desde} - {hasta}hs" if desde is not None and hasta is not None else ''
            Proveedor.objects.create(
                usuario=user,
                cuit=self.cleaned_data['cuit'],
                nombre_negocio=self.cleaned_data['nombre_negocio'],
                direccion=self.cleaned_data['direccion'],
                latitud=self.cleaned_data.get('latitud'),
                longitud=self.cleaned_data.get('longitud'),
                rubro=self.cleaned_data['rubro'],
                horarios=horarios,
                is_approved=False,
            )
        return user

class LoginForm(forms.Form):
    """Formulario de login con email"""
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput(), label="Contraseña")

class EditarPerfilTecnicoForm(forms.ModelForm):
    """Formulario para que el técnico edite su perfil"""
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")

    latitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitud = forms.FloatField(required=False, widget=forms.HiddenInput())

    field_order = ['first_name', 'last_name', 'especialidad', 'telefono', 'ubicacion', 'latitud', 'longitud']

    class Meta:
        model = Tecnico
        fields = ('especialidad', 'telefono', 'ubicacion', 'latitud', 'longitud')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name

    def save_user(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

class EditarPerfilProveedorForm(forms.ModelForm):
    """Formulario para que el proveedor edite su perfil"""
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    latitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitud = forms.FloatField(required=False, widget=forms.HiddenInput())
    horario_desde = forms.IntegerField(
        min_value=0, max_value=23, required=False, label="Desde (hs)",
        widget=forms.NumberInput(attrs={'min': 0, 'max': 23, 'placeholder': 'Ej: 9'}),
    )
    horario_hasta = forms.IntegerField(
        min_value=0, max_value=23, required=False, label="Hasta (hs)",
        widget=forms.NumberInput(attrs={'min': 0, 'max': 23, 'placeholder': 'Ej: 18'}),
    )

    field_order = [
        'first_name', 'last_name', 'nombre_negocio', 'direccion', 'latitud', 'longitud',
        'rubro', 'horario_desde', 'horario_hasta', 'logo', 'imagen',
        'banco_transferencia', 'titular_transferencia', 'cbu_transferencia', 'alias_transferencia',
    ]

    class Meta:
        model = Proveedor
        fields = (
            'nombre_negocio', 'direccion', 'latitud', 'longitud', 'rubro', 'logo', 'imagen',
            'banco_transferencia', 'titular_transferencia', 'cbu_transferencia', 'alias_transferencia',
        )
        labels = {
            'banco_transferencia': 'Banco para transferencias',
            'titular_transferencia': 'Titular de la cuenta',
            'cbu_transferencia': 'CBU / CVU',
            'alias_transferencia': 'Alias',
        }
        widgets = {
            'logo': forms.FileInput(),
            'imagen': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
        # Parsear horarios existentes ("9 - 18hs") para pre-rellenar los campos
        instance = kwargs.get('instance')
        if instance and instance.horarios:
            try:
                partes = instance.horarios.replace('hs', '').split('-')
                self.fields['horario_desde'].initial = int(partes[0].strip())
                self.fields['horario_hasta'].initial = int(partes[1].strip())
            except (ValueError, IndexError):
                pass

    def save(self, commit=True):
        proveedor = super().save(commit=False)
        desde = self.cleaned_data.get('horario_desde')
        hasta = self.cleaned_data.get('horario_hasta')
        proveedor.horarios = f"{desde} - {hasta}hs" if desde is not None and hasta is not None else ''
        if commit:
            proveedor.save()
        return proveedor

    def save_user(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
