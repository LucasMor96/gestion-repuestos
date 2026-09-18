import hashlib
import json

from django import forms
from django.core import signing

from .models import Producto


class ProductoForm(forms.ModelForm):
    """Formulario para crear y editar productos del catálogo (US-06)"""

    version_producto = forms.CharField(
        widget=forms.HiddenInput,
        error_messages={'required': 'Recargá el producto antes de guardar los cambios.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.fields.pop('version_producto')
            return
        # Compara el estado visto al abrir el formulario con la fila bloqueada
        # al enviarlo. Incluye stock, imagen y los demás campos editables.
        datos = {nombre: str(getattr(self.instance, nombre)) for nombre in self.Meta.fields_snapshot}
        self._version_actual = {
            'pk': self.instance.pk,
            'huella': hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest(),
        }
        self.initial['version_producto'] = signing.dumps(self._version_actual, salt='catalogo.producto')

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding and cleaned.get('version_producto'):
            try:
                version = signing.loads(cleaned['version_producto'], salt='catalogo.producto')
            except signing.BadSignature:
                raise forms.ValidationError('El formulario no es válido. Recargá el producto.')
            if version != self._version_actual:
                raise forms.ValidationError(
                    'El producto cambió desde que abriste el formulario. '
                    'Recargá la página para revisar el stock y volver a aplicar tus cambios.'
                )
        return cleaned

    class Meta:
        model = Producto
        fields = ('nombre', 'descripcion', 'imagen', 'modelo', 'categoria', 'precio', 'stock', 'disponible')
        fields_snapshot = fields + ('proveedor_id',)
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


class ProductoAdminForm(ProductoForm):
    class Meta(ProductoForm.Meta):
        fields = '__all__'
