"""Propadmin shared service runtime."""


def create_app(*args, **kwargs):
    from .factory import create_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app"]
