from django import forms

from .models import Credito


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
