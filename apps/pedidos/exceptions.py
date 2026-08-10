class PedidoError(Exception):
    """Error esperado al ejecutar una operacion del ciclo de pedidos."""


class EstadoPedidoInvalido(PedidoError):
    pass


class StockInsuficiente(PedidoError):
    def __init__(self, *, disponible, solicitado):
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f'Stock insuficiente. Disponible: {disponible}, solicitado: {solicitado}.'
        )
