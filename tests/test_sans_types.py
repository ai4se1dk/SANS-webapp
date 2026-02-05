"""
Tests for newly added types in sans_types.py
"""

from sans_webapp.sans_types import ChatMessage, MCPToolResult


def test_mcp_tool_result_fields():
    # Create sample tool result
    sample: MCPToolResult = {
        'tool_name': 'set-model',
        'input': {'model_name': 'sphere'},
        'result': "Model 'sphere' loaded",
        'success': True,
    }

    assert sample['tool_name'] == 'set-model'
    assert isinstance(sample['input'], dict)
    assert 'model_name' in sample['input']
    assert sample['success'] is True


def test_chat_message_with_tools():
    sample_tool = MCPToolResult(
        tool_name='set-model', input={'model_name': 'sphere'}, result='OK', success=True
    )

    msg: ChatMessage = {
        'role': 'assistant',
        'content': 'Loaded the model.',
        'tool_invocations': [sample_tool],
    }

    assert msg['role'] == 'assistant'
    assert 'tool_invocations' in msg
    assert isinstance(msg['tool_invocations'], list)
    assert msg['tool_invocations'][0]['tool_name'] == 'set-model'
