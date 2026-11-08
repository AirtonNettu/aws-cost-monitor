"""Orçamento cooperativo de tempo, sem substituir o timeout imposto pela Lambda."""

import time


class BudgetExceeded(RuntimeError):
    """Não há tempo para iniciar outra operação e finalizar com segurança."""


class Budget:
    """Combina relógio monotônico local com o tempo restante informado pela AWS."""

    def __init__(self, context, seconds=60):
        self.context = context
        self.deadline = time.monotonic() + seconds

    def require(self, seconds):
        remaining = self.deadline - time.monotonic()
        getter = getattr(self.context, "get_remaining_time_in_millis", None)
        if callable(getter):
            remaining = min(remaining, getter() / 1000)
        if remaining < seconds:
            raise BudgetExceeded("Orçamento de execução insuficiente.")
