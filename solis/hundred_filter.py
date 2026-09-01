import logging

class HundredFilter:
    def __init__(self):
        self.consecutive_100s = 0
        self.last_output = 0  # always stores the last valid numeric output
        self._LOGGER = logging.getLogger(__name__)

    def process(self, value):
        raw_value = value
        self._LOGGER.debug(
            "HundredFilter.process: raw_value=%r last_output=%s consecutive_100s=%s",
            raw_value,
            self.last_output,
            self.consecutive_100s,
        )

        # --- Validate input ---
        try:
            value = int(value)
            self._LOGGER.debug("HundredFilter.process: converted_value=%s", value)
        except (TypeError, ValueError):
            # Non-numeric → return the last valid numeric output
            self._LOGGER.debug(
                "HundredFilter.process: non_numeric input=%r, returning last_output=%s",
                raw_value,
                self.last_output,
            )
            return self.last_output

        # --- Normal values (<100) ---
        if value < 100:
            self.consecutive_100s = 0
            self.last_output = value
            self._LOGGER.debug(
                "HundredFilter.process: below_100 value=%s, setting last_output=%s, returning=%s",
                value,
                self.last_output,
                value,
            )
            return value

        # --- Value is 100 ---
        if value == 100:
            self.consecutive_100s += 1
            self._LOGGER.debug(
                "HundredFilter.process: value==100 count=%s threshold=3",
                self.consecutive_100s,
            )

            if self.consecutive_100s >= 3:
                self.last_output = 100
                self._LOGGER.debug(
                    "HundredFilter.process: threshold reached, returning 100 last_output=%s",
                    self.last_output,
                )
                return 100

            # Fallback: return last numeric output
            self._LOGGER.debug(
                "HundredFilter.process: value==100 but threshold not reached, returning last_output=%s",
                self.last_output,
            )
            return self.last_output

        # Ignore any unexpected values above 100 and keep the prior valid output
        self._LOGGER.debug(
            "HundredFilter.process: value>100 (%s), returning last_output=%s",
            value,
            self.last_output,
        )
        return self.last_output
