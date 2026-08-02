class HundredFilter:
    def __init__(self):
        self.consecutive_100s = 0
        self.last_below_100 = None

    def process(self, value):
        if value < 100:
            self.consecutive_100s = 0
            self.last_below_100 = value
            return value

        # value == 100
        self.consecutive_100s += 1

        if self.consecutive_100s >= 3:
            return 100

        return self.last_below_100