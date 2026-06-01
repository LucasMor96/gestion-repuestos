from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ProductoForm
from ..models import Producto
from .utils import get_proveedor_o_403


@login_required(login_url='login')
def catalogo_proveedor(request):
    """Lista los productos propios del proveedor."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    productos = proveedor.productos.all().order_by('nombre')
    return render(request, 'plataforma/catalogo_proveedor.html', {'productos': productos})


@login_required(login_url='login')
def agregar_producto(request):
    """Crea un nuevo producto en el catálogo."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.proveedor = proveedor
            producto.save()
            messages.success(request, f'Producto "{producto.nombre}" publicado en el catálogo.')
            return redirect('catalogo_proveedor')
    else:
        form = ProductoForm()

    return render(request, 'plataforma/producto_form.html', {'form': form, 'accion': 'Agregar'})


@login_required(login_url='login')
def editar_producto(request, pk):
    """Edita un producto existente."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('catalogo_proveedor')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'plataforma/producto_form.html', {'form': form, 'accion': 'Editar', 'producto': producto})


@login_required(login_url='login')
def eliminar_producto(request, pk):
    """Elimina un producto tras confirmación POST."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)

    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado del catálogo.')
    return redirect('catalogo_proveedor')


@login_required(login_url='login')
def toggle_disponibilidad(request, pk):
    """Activa o desactiva la visibilidad de un producto sin editar el resto."""
    proveedor = get_proveedor_o_403(request)
    if proveedor is None:
        return redirect('dashboard')

    producto = get_object_or_404(Producto, pk=pk, proveedor=proveedor)
    producto.disponible = not producto.disponible
    producto.save(update_fields=['disponible'])
    estado = 'visible' if producto.disponible else 'oculto'
    messages.success(request, f'"{producto.nombre}" ahora está {estado} en el catálogo.')
    return redirect('catalogo_proveedor')
