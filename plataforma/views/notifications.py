from django.core.mail import send_mail


def notificar_proveedor_nuevo_pedido(pedido):
    """EnvÃ­a email al proveedor cuando llega un nuevo pedido."""
    send_mail(
        subject=f'[Repuestos] Nuevo pedido #{pedido.id} â€” {pedido.producto.nombre}',
        message=(
            f'Hola {pedido.proveedor.usuario.first_name},\n\n'
            f'Recibiste un nuevo pedido en la plataforma:\n\n'
            f'  Producto : {pedido.producto.nombre}\n'
            f'  Cantidad : {pedido.cantidad}\n'
            f'  Monto    : ${pedido.monto_total}\n'
            f'  Entrega  : {pedido.get_forma_entrega_display()}\n'
            f'  TÃ©cnico  : {pedido.tecnico.usuario.get_full_name()}\n'
            f'  TelÃ©fono : {pedido.tecnico.telefono or "No informado"}\n\n'
            f'IngresÃ¡ a la plataforma para aceptar o rechazar el pedido.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[pedido.proveedor.usuario.email],
        fail_silently=True,
    )


def notificar_tecnico_estado(pedido):
    """EnvÃ­a email al tÃ©cnico cuando el proveedor cambia el estado de su pedido."""
    send_mail(
        subject=f'[Repuestos] Pedido #{pedido.id} â€” {pedido.get_estado_display()}',
        message=(
            f'Hola {pedido.tecnico.usuario.first_name},\n\n'
            f'Tu pedido fue actualizado:\n\n'
            f'  Producto  : {pedido.producto.nombre}\n'
            f'  Estado    : {pedido.get_estado_display()}\n'
            f'  Proveedor : {pedido.proveedor.nombre_negocio}\n'
            + (f'  Mensaje   : {pedido.respuesta_proveedor}\n' if pedido.respuesta_proveedor else '')
            + '\nIngresÃ¡ a la plataforma para ver el detalle de tus pedidos.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[pedido.tecnico.usuario.email],
        fail_silently=True,
    )


def notificar_credito_asignado(credito):
    send_mail(
        subject=f'[Repuestos] CrÃ©dito comercial asignado â€” {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} te asignÃ³ un crÃ©dito comercial:\n\n'
            f'  LÃ­mite disponible: ${credito.limite}\n\n'
            f'Ya podÃ©s usarlo al hacer pedidos con este proveedor.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def notificar_alerta_credito(credito):
    send_mail(
        subject=f'[Repuestos] Alerta: lÃ­mite de crÃ©dito con {credito.proveedor.nombre_negocio}',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'Usaste el {credito.porcentaje_usado}% de tu crÃ©dito con {credito.proveedor.nombre_negocio}:\n\n'
            f'  LÃ­mite total    : ${credito.limite}\n'
            f'  Saldo usado     : ${credito.saldo_usado}\n'
            f'  Saldo disponible: ${credito.saldo_disponible}\n\n'
            f'Por favor, regularizÃ¡ tu deuda para seguir usando el crÃ©dito.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def notificar_deuda_saldada(credito):
    send_mail(
        subject=f'[Repuestos] Tu deuda con {credito.proveedor.nombre_negocio} fue saldada',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} marcÃ³ tu deuda como saldada.\n\n'
            f'Tu crÃ©dito disponible se restableciÃ³. LÃ­mite: ${credito.limite}\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )


def notificar_credito_revocado(credito):
    send_mail(
        subject=f'[Repuestos] Tu crÃ©dito con {credito.proveedor.nombre_negocio} fue revocado',
        message=(
            f'Hola {credito.tecnico.usuario.first_name},\n\n'
            f'{credito.proveedor.nombre_negocio} revocÃ³ tu crÃ©dito comercial.\n\n'
            f'Si tenÃ©s saldo pendiente, contactÃ¡ al proveedor para regularizar tu situaciÃ³n.\n'
        ),
        from_email='noreply@gestion-repuestos.com',
        recipient_list=[credito.tecnico.usuario.email],
        fail_silently=True,
    )
