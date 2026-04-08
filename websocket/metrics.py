class Metrics:
    def __init__(self):
        self.messages_received = 0
        self.messages_delivered = 0
        self.auth_failures = 0
        self.latencies: list = []

    def record_latency(self, latency_ms):
        self.latencies.append(latency_ms)
        if len(self.latencies) > 1000:
            self.latencies.pop(0)

    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0
    