from __future__ import annotations
from importlib import import_module


def violation(rule: str, severity: str, message: str) -> dict:
    return {'rule': rule, 'severity': severity, 'message': message}


def check_all(entry: dict) -> list[dict]:
    return [v for number in range(1, 11) for v in import_module(f'{__name__}.c{number}').check(entry)]
