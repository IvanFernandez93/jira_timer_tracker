import pytest
from services.jira_service import JiraService
from jira import JIRAError

class DummyJiraError(JIRAError):
    def __init__(self, status_code=None, text=None, response=None):
        self.status_code = status_code
        self.text = text
        self.response = response
        super().__init__(status_code)


def test_with_retries_succeeds_after_retries():
    calls = {'n': 0}

    def flaky():
        calls['n'] += 1
        if calls['n'] < 3:
            raise Exception('transient')
        return 'ok'

    js = JiraService(max_retries=5, sleep_func=lambda s: None)
    result = js._with_retries(flaky)
    assert result == 'ok'
    assert calls['n'] == 3


def test_with_retries_non_retryable_jira_error():
    def bad_request():
        e = DummyJiraError(status_code=400, text='Bad Request')
        raise e

    js = JiraService(max_retries=3, sleep_func=lambda s: None)
    with pytest.raises(DummyJiraError):
        js._with_retries(bad_request)


def test_with_retries_respects_max_attempts():
    calls = {'n': 0}
    def always_fail():
        calls['n'] += 1
        raise Exception('network')

    js = JiraService(max_retries=2, sleep_func=lambda s: None)
    with pytest.raises(Exception):
        js._with_retries(always_fail)
    assert calls['n'] == 2
