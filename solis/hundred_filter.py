class HundredFilter:
    def __init__(self):
        self.consecutive_100s = 0
        self.last_output = None  # always stores the last returned numeric value

    def process(self, value):
        # --- Validate input ---
        try:
            value = int(value)
        except (TypeError, ValueError):
            # Non-numeric → return last known numeric output
            return self.last_output

        # --- Normal values (<100) ---
        if value < 100:
            self.consecutive_100s = 0
            self.last_output = value
            return value

        # --- Value is 100 ---
        self.consecutive_100s += 1

        if self.consecutive_100s >= 3:
            self.last_output = 100
            return 100

        # Fallback: return last numeric output
        return self.last_output
