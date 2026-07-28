class NegativeStock(Exception):
    """Raised when an adjustment would drive stock below zero."""
    def __init__(self, current_quantity, delta):
        self.current_quantity = current_quantity
        self.delta = delta
        super().__init__(
            f'No puedes ajustar {delta:+d}: solo hay {current_quantity} en existencia.'
        )
