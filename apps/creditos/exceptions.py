class CreditoError(Exception):
    """Error esperado al operar sobre credito comercial."""


class CreditoNoDisponible(CreditoError):
    pass


class SaldoInsuficiente(CreditoError):
    def __init__(self, *, disponible, solicitado):
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__('El monto supera el credito disponible.')


class DeudaInexistente(CreditoError):
    pass
