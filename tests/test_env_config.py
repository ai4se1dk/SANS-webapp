"""
Tests for environment configuration: .env.template and ANTHROPIC_API_KEY handling.
"""
from unittest.mock import MagicMock, patch

import os


def test_env_template_contains_keys():
    path = os.path.join(os.path.dirname(__file__), os.pardir, '.env.template')
    path = os.path.abspath(path)

    with open(path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    assert 'ANTHROPIC_API_KEY' in content, '.env.template should contain ANTHROPIC_API_KEY'
    assert 'OPENAI_API_KEY' not in content, '.env.template should not contain OPENAI_API_KEY (replaced by Anthropic)'



def test_init_mcp_uses_anthropic_env_var_if_no_session_key():
    from sans_webapp import app

    mock_st = MagicMock()
    mock_st.session_state = MagicMock()
    # No chat_api_key in session_state (ensure .get() returns None)
    mock_st.session_state.get.return_value = None
    mock_st.session_state.fitter = 'FAKE_FITTER'

    with patch.object(app, 'st', mock_st):
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'ENV_KEY'}, clear=True):
            with patch('sans_webapp.mcp_server.set_fitter') as mock_set_fitter, patch(
                'sans_webapp.mcp_server.set_state_accessor'
            ) as mock_set_accessor, patch(
                'sans_webapp.services.claude_mcp_client.get_claude_client'
            ) as mock_get_client:
                app.init_mcp_and_ai()

                mock_set_fitter.assert_called_once_with('FAKE_FITTER')
                mock_set_accessor.assert_called_once_with(mock_st.session_state)
                mock_get_client.assert_called_once_with('ENV_KEY')


def test_readme_mentions_anthropic_key():
    readme_path = os.path.join(os.path.dirname(__file__), os.pardir, 'WEBAPP_README.md')
    readme_path = os.path.abspath(readme_path)

    with open(readme_path, 'r', encoding='utf-8') as fh:
        content = fh.read()

    assert 'ANTHROPIC_API_KEY' in content, 'WEBAPP_README.md should document ANTHROPIC_API_KEY'
