"""Select native agent login material without carrying unrelated MCP credentials."""


def login_contents(provider, value):
    """Return only the selected provider's supported login fields from a credential file."""
    if not isinstance(value, dict):
        return {}
    if provider == 'claude':
        oauth = value.get('claudeAiOauth')
        return {'claudeAiOauth': oauth} if isinstance(oauth, dict) else {}
    if provider == 'codex':
        return {key: value[key] for key in ('auth_mode', 'OPENAI_API_KEY', 'tokens', 'last_refresh') if key in value}
    if provider == 'cursor':
        return {key: value[key] for key in ('accessToken', 'refreshToken') if key in value}
    raise ValueError('Unsupported agent credential provider')


def has_login(provider, value):
    """Distinguish a native refreshable login from an empty file or snapshot placeholder."""
    value = login_contents(provider, value)
    if provider == 'claude':
        value = value.get('claudeAiOauth', {})
        fields = ('accessToken', 'refreshToken')
    elif provider == 'codex':
        if isinstance(value.get('OPENAI_API_KEY'), str) and value['OPENAI_API_KEY']:
            return True
        value = value.get('tokens') or {}
        fields = ('access_token', 'refresh_token')
    else:
        fields = ('accessToken', 'refreshToken')
    return isinstance(value, dict) and any(isinstance(value.get(key), str) and value[key] for key in fields)
