import csv

from django.http import HttpResponse


def exportar_historial_csv(pedidos):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="historial_pedidos.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['#', 'Producto', 'Proveedor', 'Cantidad', 'Entrega', 'Pago', 'Monto ($)', 'Estado', 'Fecha'])
    for pedido in pedidos:
        writer.writerow([
            pedido.id,
            pedido.producto.nombre,
            pedido.proveedor.nombre_negocio,
            pedido.cantidad,
            pedido.get_forma_entrega_display(),
            pedido.get_forma_pago_display(),
            pedido.monto_total,
            pedido.get_estado_display(),
            pedido.fecha_creacion.strftime('%d/%m/%Y'),
        ])
    return response
