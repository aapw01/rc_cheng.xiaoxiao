from http import HTTPStatus

from scripts.mock_vendor import Handler


def test_mock_vendor_default_status_is_ok():
    assert Handler.response_status_for("/api/contacts/subscription-paid", {}) == HTTPStatus.OK


def test_mock_vendor_path_can_force_failure_status():
    assert Handler.response_status_for("/fail-500", {}) == HTTPStatus.INTERNAL_SERVER_ERROR


def test_mock_vendor_header_can_force_status():
    assert (
        Handler.response_status_for("/api/contacts/subscription-paid", {"X-Mock-Status": "503"})
        == HTTPStatus.SERVICE_UNAVAILABLE
    )


def test_mock_vendor_ignores_invalid_forced_status():
    assert Handler.response_status_for("/fail-999", {"X-Mock-Status": "nope"}) == HTTPStatus.OK
