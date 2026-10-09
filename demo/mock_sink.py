"""Local-only mock recipient: zero network code and zero real integrations."""


class MockDeliveryError(RuntimeError):
    """Synthetic receiver intentionally failed."""


class MockSink:
    def __init__(self, fail=False):
        self.deliveries = []
        self.fail = fail

    def deliver(self, task_id, new_state):
        if self.fail:
            raise MockDeliveryError('synthetic mock delivery failure')
        self.deliveries.append({'task_id': task_id, 'state': new_state})
