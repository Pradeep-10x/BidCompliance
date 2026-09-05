class SplitAssigner:
    """Leak-safe deterministic split assignment within each document type."""

    def assign_for_index(self, index: int, total: int) -> str:
        if total <= 0:
            raise ValueError("total must be positive")
        train_n = int(total * 0.70)
        val_n = int(total * 0.15)
        # Keep at least one validation/test sample when the requested total allows it.
        if total >= 3:
            train_n = min(train_n, total - 2)
            val_n = max(1, val_n)
        if index < train_n:
            return "train"
        if index < train_n + val_n:
            return "val"
        return "test"
