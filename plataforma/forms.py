from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Tecnico, Proveedor, Producto, Pedido, Credito, CalificacionProveedor, CalificacionTecnico, RUBROS_CHOICES


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
    ]

    class Meta:
        model = Proveedor
        fields = ('nombre_negocio', 'direccion', 'latitud', 'longitud', 'rubro', 'logo', 'imagen')
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


class ProductoForm(forms.ModelForm):
    """Formulario para crear y editar productos del catálogo (US-06)"""

    class Meta:
        model = Producto
        fields = ('nombre', 'descripcion', 'imagen', 'modelo', 'categoria', 'precio', 'stock', 'disponible')
        labels = {
            'nombre': 'Nombre del producto',
            'descripcion': 'Descripción',
            'imagen': 'Imagen del producto',
            'modelo': 'Modelo / Compatibilidad',
            'categoria': 'Categoría',
            'precio': 'Precio ($)',
            'stock': 'Stock disponible',
            'disponible': 'Visible en el catálogo',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'imagen': forms.FileInput(),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a cero.')
        return precio


class GestionarPedidoForm(forms.Form):
    """Formulario para que el proveedor acepte, rechace o proponga alternativa (US-08)"""
    ACCION_CHOICES = [
        ('aceptar', 'Aceptar pedido'),
        ('rechazar', 'Rechazar pedido'),
        ('alternativa', 'Proponer alternativa'),
    ]
    accion = forms.ChoiceField(
        choices=ACCION_CHOICES,
        widget=forms.RadioSelect,
        label='Acción',
    )
    respuesta = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Motivo del rechazo o descripción de la alternativa que proponés...',
        }),
        required=False,
        label='Mensaje para el técnico',
    )

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get('accion')
        respuesta = (cleaned_data.get('respuesta') or '').strip()
        if accion == 'alternativa' and not respuesta:
            raise forms.ValidationError(
                'Debés describir la alternativa que proponés al técnico.'
            )
        return cleaned_data


class PedidoForm(forms.ModelForm):
    """Formulario para que un tecnico solicite un repuesto (US-07)"""

    direccion_envio = forms.CharField(
        max_length=255,
        required=False,
        label='Direccion de entrega',
        widget=forms.TextInput(attrs={
            'class': 'form-control border-2',
            'placeholder': 'Ej: Av. San Martin 2450, Rosario',
        }),
    )
    telefono_contacto = forms.CharField(
        max_length=30,
        required=False,
        label='Telefono de contacto',
        widget=forms.TextInput(attrs={
            'class': 'form-control border-2',
            'placeholder': 'Ej: 341 555-0198',
        }),
    )
    franja_horaria = forms.ChoiceField(
        choices=[
            ('', 'Selecciona una franja'),
            ('manana', 'Manana, 9 a 13 hs'),
            ('tarde', 'Tarde, 13 a 18 hs'),
            ('noche', 'Ultimo reparto, 18 a 21 hs'),
        ],
        required=False,
        label='Franja horaria',
        widget=forms.Select(attrs={'class': 'form-select border-2'}),
    )
    class Meta:
        model = Pedido
        fields = ('cantidad', 'forma_entrega', 'notas')
        labels = {
            'cantidad': 'Cantidad',
            'forma_entrega': 'Forma de entrega',
            'notas': 'Notas adicionales (opcional)',
        }
        widgets = {
            'notas': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Instrucciones especiales, dirección de entrega, etc.',
            }),
        }

    def __init__(self, *args, stock=None, tecnico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._stock = stock
        self.fields['forma_entrega'].choices = Pedido.ENTREGA_CHOICES
        self.fields['cantidad'].widget.attrs.update({'min': 1, 'class': 'form-control rounded-pill border-2'})
        if stock is not None:
            self.fields['cantidad'].widget.attrs['max'] = stock
        if tecnico is not None:
            self.fields['direccion_envio'].initial = tecnico.ubicacion
            self.fields['telefono_contacto'].initial = tecnico.telefono

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a cero.')
        if self._stock is not None and cantidad is not None and cantidad > self._stock:
            raise forms.ValidationError(f'Solo hay {self._stock} unidades disponibles en stock.')
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('forma_entrega') == 'envio':
            for field_name in ('direccion_envio', 'telefono_contacto', 'franja_horaria'):
                if not (cleaned_data.get(field_name) or '').strip():
                    self.add_error(field_name, 'Completa este dato para coordinar el envio.')
        return cleaned_data


class AsignarCreditoForm(forms.ModelForm):
    """Formulario para que un proveedor asigne o edite el límite de crédito de un técnico (US-11)"""

    class Meta:
        model = Credito
        fields = ('limite',)
        labels = {'limite': 'Límite de crédito ($)'}
        widgets = {
            'limite': forms.NumberInput(attrs={
                'min': '0.01',
                'step': '0.01',
                'placeholder': 'Ej: 50000',
                'class': 'form-control border-2',
            }),
        }

    def clean_limite(self):
        limite = self.cleaned_data.get('limite')
        if limite is not None and limite <= 0:
            raise forms.ValidationError('El límite debe ser mayor a cero.')
        return limite


class CalificacionProveedorForm(forms.ModelForm):
    """Formulario para que un técnico califique a un proveedor (US-13)"""
    estrellas = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        label="Calificación",
        error_messages={
            'required': 'Seleccioná una calificación de 1 a 5 estrellas.',
            'min_value': 'La calificación mínima es 1 estrella.',
            'max_value': 'La calificación máxima es 5 estrellas.',
        },
    )
    comentario = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Compartí tu experiencia con este proveedor (opcional)...',
            'class': 'form-control rounded-3',
        }),
        required=False,
        label="Comentario (opcional)",
    )

    class Meta:
        model = CalificacionProveedor
        fields = ('estrellas', 'comentario')


class CalificacionTecnicoForm(forms.ModelForm):
    """Formulario para que un proveedor califique a un técnico (US-14)"""
    puntualidad = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        label="Puntualidad de pago",
        error_messages={
            'required': 'Seleccioná una calificación de puntualidad.',
            'min_value': 'La calificación mínima es 1 estrella.',
            'max_value': 'La calificación máxima es 5 estrellas.',
        },
    )
    trato = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        label="Trato",
        error_messages={
            'required': 'Seleccioná una calificación de trato.',
            'min_value': 'La calificación mínima es 1 estrella.',
            'max_value': 'La calificación máxima es 5 estrellas.',
        },
    )
    comentario_privado = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Comentario privado sobre este técnico (visible solo para otros proveedores)...',
            'class': 'form-control rounded-3',
        }),
        required=False,
        label="Comentario privado (opcional)",
    )

    class Meta:
        model = CalificacionTecnico
        fields = ('puntualidad', 'trato', 'comentario_privado')
