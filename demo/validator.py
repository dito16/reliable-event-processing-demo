"""Validation for a small fictional task-event format."""

KINDS = frozenset({'task_created', 'task_started', 'task_completed', 'task_failed'})


class InvalidEvent(ValueError):
    """A synthetic input event violates the demo schema."""


def validate(value):
    if not isinstance(value, dict):
        raise InvalidEvent('event must be a JSON object')
    allowed = {'event_id', 'task_id', 'kind', 'title'}
    if set(value) - allowed:
        raise InvalidEvent('unexpected fields')
    for field in ('event_id', 'task_id', 'kind'):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise InvalidEvent(f'invalid or missing {field}')
    if value['kind'] not in KINDS:
        raise InvalidEvent('unknown event kind')
    if value['kind'] == 'task_created':
        if not isinstance(value.get('title'), str) or not value['title'].strip():
            raise InvalidEvent('new task needs a title')
    elif 'title' in value:
        raise InvalidEvent('title is only allowed on creation')
    return value
