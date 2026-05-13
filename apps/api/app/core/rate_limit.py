"""Shared SlowAPI limiter instance (route decorators must reference this same object)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[], headers_enabled=True)
