import pytest
from unittest.mock import patch, MagicMock
from gmail_gateway import GmailGateway, GmailMessage, GmailListMessagesResponse

@pytest.fixture
def fake_token():
    return 'fake-access-token'

@pytest.fixture
def gateway(fake_token):
    return GmailGateway(fake_token)

@patch('gmail_gateway.requests.Session')
def test_list_messages(mock_session, gateway):
    mock_instance = mock_session.return_value
    # Mock the /messages list response
    mock_instance.get.side_effect = [
        MagicMock(status_code=200, json=lambda: {
            'messages': [{'id': '1', 'threadId': 't1'}],
            'nextPageToken': 'abc',
            'resultSizeEstimate': 1
        }),
        MagicMock(status_code=200, json=lambda: {
            'id': '1', 'threadId': 't1', 'snippet': 'hello', 'labelIds': ['INBOX'], 'payload': {}, 'sizeEstimate': 1234
        })
    ]
    resp = gateway.list_messages()
    assert isinstance(resp, GmailListMessagesResponse)
    assert resp.nextPageToken == 'abc'
    assert resp.resultSizeEstimate == 1
    assert len(resp.messages) == 1
    assert resp.messages[0].id == '1'
    assert resp.messages[0].snippet == 'hello'

@patch('gmail_gateway.requests.Session')
def test_get_message(mock_session, gateway):
    mock_instance = mock_session.return_value
    mock_instance.get.return_value = MagicMock(status_code=200, json=lambda: {
        'id': '2', 'threadId': 't2', 'snippet': 'test', 'labelIds': ['INBOX'], 'payload': {}, 'sizeEstimate': 4321
    })
    msg = gateway.get_message('2')
    assert isinstance(msg, GmailMessage)
    assert msg.id == '2'
    assert msg.snippet == 'test'
