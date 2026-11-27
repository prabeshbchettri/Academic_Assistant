from workflow.nodes import normalize_node


def test_normalize_node_with_empty_state_uses_manual_source_type():
    result = normalize_node({})

    assert result["normalized_input"]["source_type"] == "manual"
    assert result["normalized_input"]["title"] == "Academic Assignment"
    assert result["node_history"] == ["normalize"]
    assert result["status"] == "in_progress"
