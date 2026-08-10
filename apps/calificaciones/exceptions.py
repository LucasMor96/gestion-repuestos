class CalificacionError(Exception):
    pass


class PedidoNoCompletado(CalificacionError):
    pass


class CalificacionDuplicada(CalificacionError):
    pass


class ActorInvalido(CalificacionError):
    pass
