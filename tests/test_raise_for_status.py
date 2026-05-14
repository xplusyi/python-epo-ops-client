import pytest
import responses
from pytest import raises
from requests.exceptions import HTTPError

from epo_ops.api import Client
from epo_ops.models import Docdb


@pytest.fixture
def ops_backend_413():
    """
    Emulate an OPS backend returning 413 on the fulltext endpoint for an
    ambiguous input. The real upstream returns 413 for e.g. EP.0536425/fulltext.
    """
    token = responses.Response(
        responses.POST,
        url="https://ops.epo.org/3.2/auth/accesstoken",
        status=200,
        json={"access_token": "foo", "expires_in": 42},
    )
    fulltext_413 = responses.Response(
        responses.POST,
        url="https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/fulltext",
        status=413,
        headers={"Content-Type": "application/xml"},
        body=(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '  <fault xmlns="http://ops.epo.org">\n'
            "    <code>CLIENT.AmbiguousRequest</code>\n"
            "    <message>The request was ambiguous</message>\n"
            "    <details>\n"
            "      <cause>Ambiguous input: publication/docdb/EP.0536425</cause>\n"
            "      <resolution>publication/docdb/EP.0536425.A1</resolution>\n"
            "      <resolution>publication/docdb/EP.0536425.A4</resolution>\n"
            "      <resolution>publication/docdb/EP.0536425.B1</resolution>\n"
            "      <resolution>publication/docdb/EP.0536425.B2</resolution>\n"
            "    </details>\n"
            "  </fault>"
        ),
    )
    for response in [token, fulltext_413]:
        responses.add(response)


def _issue_fulltext_request(client):
    return client.published_data(
        "publication",
        Docdb("0536425", "EP", "B1"),
        endpoint="fulltext",
    )


@responses.activate
def test_413_raises_by_default(ops_backend_413):
    client = Client("key", "secret", middlewares=[])
    with raises(HTTPError):
        _issue_fulltext_request(client)


@responses.activate
def test_413_returned_when_raise_for_status_disabled(ops_backend_413):
    client = Client("key", "secret", middlewares=[], raise_for_status=False)
    response = _issue_fulltext_request(client)
    assert response.status_code == 413
    assert "CLIENT.AmbiguousRequest" in response.text
    assert "publication/docdb/EP.0536425.B1" in response.text
