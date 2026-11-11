"""Errores que el conector distingue al hablar con los servicios externos."""


class ConnectorError(Exception):
    """Base de los errores del conector."""


class TransientError(ConnectorError):
    """Fallo que puede desaparecer al reintentar: timeout, 429 o 5xx."""


class PermanentError(ConnectorError):
    """Fallo que no cambia al reintentar: datos inválidos, 4xx distinto de 429."""
