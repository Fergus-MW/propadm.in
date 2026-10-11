"""Voice reconciliation must preserve the authenticated initiation webhook."""

from infra.scripts.configure_voice import configuration


def test_voice_configuration_preserves_workspace_overrides_and_existing_tools():
    initiation = {'url': 'https://voice.example.test/initiation',
                  'request_headers': {'X-Webhook-Secret': {'secret_id': 'test-secret'}}}
    current = {
        'conversation_config': {'agent': {'first_message': 'Propadmin assistant', 'prompt': {
            'prompt': 'Use the graph tools.', 'tool_ids': ['graph-tools'],
            'built_in_tools': {'transfer_to_number': {'type': 'system'}},
        }}},
        'platform_settings': {'workspace_overrides': {
            'conversation_initiation_client_data_webhook': initiation,
            'cloud_storage_export': {'enabled': True},
            'webhooks': {'post_call_webhook_id': 'post-call', 'events': ['transcript']},
        }},
    }
    result = configuration(current)
    overrides = result['platform_settings']['workspace_overrides']
    assert overrides['conversation_initiation_client_data_webhook'] == initiation
    assert overrides['cloud_storage_export'] == {'enabled': True}
    assert overrides['webhooks']['post_call_webhook_id'] == 'post-call'
    assert overrides['webhooks']['events'] == ['transcript', 'call_initiation_failure']
    assert 'transfer_to_number' in result['conversation_config']['agent']['prompt']['built_in_tools']
    assert result['conversation_config']['agent']['first_message'] == 'Properly assistant'
