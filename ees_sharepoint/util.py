"""util module contains general utility classes."""

class Singleton(type):
    """Singleton class provides a metaclass for Singeton pattern.

    Can be used by defining class Something(metaclass=Singleton)"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
