"""Pure unit tests for the independently designed fictional task-event schema."""
import unittest

from demo.validator import InvalidEvent, validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.created = {
            'event_id': 'event-1', 'task_id': 'task-1',
            'kind': 'task_created', 'title': 'Organize sample folders',
        }

    def test_valid_created_event(self):
        self.assertEqual(validate(self.created), self.created)

    def test_valid_transition_without_title(self):
        for kind in ('task_started', 'task_completed', 'task_failed'):
            with self.subTest(kind=kind):
                self.assertEqual(validate({
                    'event_id': 'e', 'task_id': 't', 'kind': kind,
                })['kind'], kind)

    def test_non_object_rejected(self):
        for value in (None, [], 'event', 5, True):
            with self.subTest(value=value), self.assertRaises(InvalidEvent):
                validate(value)

    def test_missing_required_fields_rejected(self):
        for key in ('event_id', 'task_id', 'kind'):
            with self.subTest(key=key), self.assertRaises(InvalidEvent):
                validate({k: v for k, v in self.created.items() if k != key})

    def test_blank_required_fields_rejected(self):
        for key in ('event_id', 'task_id', 'kind'):
            with self.subTest(key=key), self.assertRaises(InvalidEvent):
                validate({**self.created, key: ' \t'})

    def test_nonstring_required_fields_rejected(self):
        for value in (0, False, [], {}, None):
            with self.subTest(value=value), self.assertRaises(InvalidEvent):
                validate({**self.created, 'event_id': value})

    def test_unknown_event_kind_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({**self.created, 'kind': 'task_rescheduled'})

    def test_unexpected_field_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({**self.created, 'secret_field': 'not allowed'})

    def test_missing_create_title_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({k: v for k, v in self.created.items() if k != 'title'})

    def test_blank_create_title_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({**self.created, 'title': '   '})

    def test_nonstring_create_title_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({**self.created, 'title': 123})

    def test_title_on_non_creation_rejected(self):
        with self.assertRaises(InvalidEvent):
            validate({**self.created, 'kind': 'task_started'})


if __name__ == '__main__':
    unittest.main()
