from django import forms

from .models import CalificacionProveedor, CalificacionTecnico


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
