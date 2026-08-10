from django import forms

from .models import Producto


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
