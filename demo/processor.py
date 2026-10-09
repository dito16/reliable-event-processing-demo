"""Local event ingestion and durable synthetic outbox dispatch."""

from .mock_sink import MockDeliveryError
from .validator import InvalidEvent, validate


def run_batch(raw_events, sink, store):
    counters = {'processed': 0, 'ignored': 0, 'rejected': 0}
    for raw in raw_events:
        try:
            event = validate(raw)
            result = store.record(event)
        except InvalidEvent:
            counters['rejected'] += 1
        else:
            counters[result] += 1

    delivery_failures = 0
    for delivery_id, task_id, new_state in store.pending():
        try:
            sink.deliver(task_id, new_state)
        except MockDeliveryError:
            delivery_failures += 1
            break  # Leave pending rows unacknowledged for an explicit later retry.
        store.acknowledge(delivery_id)

    return {
        **counters,
        'deliveries': len(sink.deliveries),
        'delivery_failures': delivery_failures,
        'pending': store.pending_count(),
        'states': store.states(),
    }
