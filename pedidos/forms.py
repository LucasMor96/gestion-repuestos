from django import forms

from .models import Pedido


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
