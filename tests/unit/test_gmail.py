from unittest.mock import MagicMock

from integrations.gmail.client import search_messages


def test_search_messages_mock():
    mock_service = MagicMock()
    mock_messages_resource = mock_service.users().messages()
    mock_messages_resource.list().execute.return_value = {
        "messages": [{"id": "msg_001"}, {"id": "msg_002"}]
    }

    mock_messages_resource.get().execute.side_effect = [
        {
            "id": "msg_001",
            "snippet": "Homework 1 due Friday",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Physics Assignment 1"},
                    {"name": "From", "value": "prof@univ.edu"},
                    {"name": "Date", "value": "2026-11-20"},
                ]
            },
        },
        {
            "id": "msg_002",
            "snippet": "Lab report guidelines attached",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Lab 2 Guidelines"},
                    {"name": "From", "value": "ta@univ.edu"},
                    {"name": "Date", "value": "2026-11-21"},
                ]
            },
        },
    ]

    results = search_messages(mock_service, query="assignment", max_results=10)
    assert len(results) == 2
    assert results[0]["subject"] == "Physics Assignment 1"
    assert results[1]["sender"] == "ta@univ.edu"
