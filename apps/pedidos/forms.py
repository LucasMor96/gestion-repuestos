from decimal import Decimal
from uuid import uuid4

from django import forms

from apps.catalogo.models import Producto

from .models import Pedido


class GestionarPedidoForm(forms.Form):
    """Formulario para que el proveedor acepte, rechace o proponga alternativa (US-08)"""
    ACCION_CHOICES = [
        ('aceptar', 'Aceptar pedido'),
        ('rechazar', 'Rechazar pedido'),
        ('alternativa', 'Proponer alternativa'),
        ('cancelar', 'Cancelar pedido'),
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
    producto_alternativo = forms.ModelChoiceField(
        queryset=Producto.objects.none(),
        required=False,
        empty_label='Elegí un producto de tu catálogo',
        label='Producto alternativo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    limite_credito = forms.DecimalField(
        required=False, min_value=Decimal('0.01'), max_digits=12, decimal_places=2,
        label='Límite total del cupo reutilizable ($)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )

    def __init__(self, *args, solicitud_credito=False, productos_alternativos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud_credito = solicitud_credito
        if productos_alternativos is not None:
            self.fields['producto_alternativo'].queryset = productos_alternativos
        if not solicitud_credito:
            self.fields.pop('limite_credito')
        elif self.is_bound and self.data.get('accion') != 'aceptar':
            # El rechazo no depende del valor de un cupo que no se va a otorgar.
            self.fields['limite_credito'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get('accion')
        respuesta = (cleaned_data.get('respuesta') or '').strip()
        if self.solicitud_credito and accion == 'aceptar' and cleaned_data.get('limite_credito') is None:
            self.add_error('limite_credito', 'Indicá el límite de crédito que querés otorgar.')
        if accion == 'alternativa' and not cleaned_data.get('producto_alternativo'):
            self.add_error('producto_alternativo', 'Elegí el producto que querés ofrecer como alternativa.')
        return cleaned_data

class PedidoForm(forms.ModelForm):
    """Formulario para que un tecnico solicite un repuesto (US-07)"""

    clave_operacion = forms.UUIDField(
        initial=uuid4,
        widget=forms.HiddenInput,
        error_messages={
            'required': 'Recargá la página para iniciar un nuevo pedido.',
            'invalid': 'La solicitud no es válida. Recargá la página e intentá nuevamente.',
        },
    )

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
        fields = ('cantidad', 'forma_entrega', 'forma_pago', 'comprobante_transferencia', 'notas')
        labels = {
            'cantidad': 'Cantidad',
            'forma_entrega': 'Forma de entrega',
            'forma_pago': 'Forma de pago',
            'comprobante_transferencia': 'Comprobante de transferencia',
            'notas': 'Notas adicionales (opcional)',
        }
        widgets = {
            'comprobante_transferencia': forms.FileInput(attrs={
                'class': 'form-control border-2',
                'accept': 'image/*,.pdf',
            }),
            'notas': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Instrucciones especiales, dirección de entrega, etc.',
            }),
        }

    def __init__(self, *args, stock=None, tecnico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._stock = stock
        self.fields['forma_entrega'].choices = Pedido.ENTREGA_CHOICES
        self.fields['forma_pago'].choices = Pedido.FORMA_PAGO_CHOICES
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
        if cleaned_data.get('forma_pago') == 'transferencia' and not cleaned_data.get('comprobante_transferencia'):
            self.add_error('comprobante_transferencia', 'Subi el comprobante para pagar por transferencia.')
        return cleaned_data
