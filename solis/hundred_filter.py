class HundredFilter:
    def __init__(self):
        self.consecutive_100s = 0
        self.last_output = 0  # always stores the last valid numeric output

    def process(self, value):
        # --- Validate input ---
        try:
            value = int(value)
        except (TypeError, ValueError):
            # Non-numeric → return the last valid numeric output
            return self.last_output

        # --- Normal values (<100) ---
        if value < 100:
            self.consecutive_100s = 0
            self.last_output = value
            return value

        # --- Value is 100 ---
        if value == 100:
            self.consecutive_100s += 1

            if self.consecutive_100s >= 3:
                self.last_output = 100
                return 100

            # Fallback: return last numeric output
            return self.last_output

        # Ignore any unexpected values above 100 and keep the prior valid output
        return self.last_output
