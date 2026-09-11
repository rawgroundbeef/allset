"""Validate project configuration independently of a developer's active login."""

import base64
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse


def identifier(value):
    """Require a short DNS-safe identifier for paths, labels and preview hosts."""
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,29}', value):
        raise ValueError('Project and service IDs must be lowercase DNS labels, at most 30 characters.')
    return value


def validate(profile):
    """Reject incomplete profiles, inline credentials and ambiguous project bindings."""
    identifier(profile['name'])
    if profile['version'] not in (1, 2):
        raise ValueError('Unsupported profile version')
    for field in ('repository', 'base', 'template', 'box_environment', 'setup_commands', 'services'):
        if field not in profile:
            raise ValueError('Missing profile field: ' + field)
    for alias in profile.get('aliases', []): identifier(alias)
    if profile.get('agent_profile'): identifier(profile['agent_profile'])
    if 'github' in profile:
        from github_auth import validate as validate_github
        validate_github(profile['github'])
    coding_only = profile.get('coding_only') is True
    if coding_only:
        if profile['version'] < 2 or profile['services'] or profile['setup_commands']:
            raise ValueError('A coding-only profile cannot declare app setup or services')
        binding = profile.get('provider_binding') or {}
        if (binding.get('provider'), binding.get('environment'), binding.get('safe_for_third_parties')) != (
                'box', profile['box_environment'], True):
            raise ValueError('A coding-only profile requires its owned no-ambient-injection Box environment')
        identity = binding.get('account_identity') or {}
        if not isinstance(identity, dict) or not identity or set(identity) - {'id', 'email'}:
            raise ValueError('A coding-only profile requires an explicit Box account identity')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', binding.get('billing_scope', '')):
            raise ValueError('A coding-only profile requires an explicit Box billing organization')
        clients = profile.get('clients') or []
        if not clients or len(set(clients)) != len(clients) or set(clients) - {'codex', 'claude', 'cursor'}:
            raise ValueError('A coding-only profile requires selected coding clients')
        names = set()
        for skill in profile.get('personal_skills') or []:
            name = identifier(skill.get('name'))
            path = Path(skill.get('path', '')).expanduser()
            if name in names or not path.is_absolute():
                raise ValueError('Personal skill bindings require unique names and absolute private paths')
            names.add(name)
        if profile.get('infisical') is None:
            return profile
    if profile.get('shell_only'):
        if profile.get('infisical') is not None or profile['services']:
            raise ValueError('A shell-only profile cannot claim configured app secrets or services')
        return profile
    if not coding_only and not profile['setup_commands']:
        raise ValueError('At least one dependency setup/check command is required')
    auth = profile['infisical']
    url = urlparse(auth['instance'])
    if url.scheme != 'https' or not url.hostname or url.username or url.query or url.path not in ('', '/', '/api'):
        raise ValueError('Infisical instance must be an explicit HTTPS origin')
    for field in ('organization_id', 'project_id', 'environment', 'credential_ref', 'principal_id'):
        if not auth.get(field):
            raise ValueError('Missing Infisical field: ' + field)
    if set(auth) - {'instance', 'organization_id', 'project_id', 'environment', 'credential_ref',
                    'principal_id', 'user_email', 'permission_note'}:
        raise ValueError('Unexpected Infisical field; credentials belong only in credential_ref')
    if not Path(auth['credential_ref']).expanduser().is_absolute():
        raise ValueError('credential_ref must be an absolute private file path')
    if coding_only:
        return profile
    if profile.get('preview_domain') and not re.fullmatch(r'[a-z][a-z0-9.-]*\.localhost', profile['preview_domain']):
        raise ValueError('Preview domain must be an explicit project .localhost name')
    names = set()
    for service in profile['services']:
        name = identifier(service['name'])
        if name in names:
            raise ValueError('Duplicate service name')
        names.add(name)
        cwd = Path(service['cwd'])
        if cwd.is_absolute() or '..' in cwd.parts:
            raise ValueError('Service cwd must stay inside its worktree')
        if not service['command'] or not isinstance(service['command'], list):
            raise ValueError('Service command must be an argv list')
        for path in service['secret_paths']:
            if not path.startswith('/') or '..' in Path(path).parts:
                raise ValueError('Invalid secret path')
    if profile['preview_service'] not in names:
        raise ValueError('Preview must select a configured service')
    return profile


def claims(token):
    """Decode public token claims for binding checks; the Infisical API verifies authenticity."""
    try:
        return json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '==='))
    except (ValueError, IndexError):
        raise ValueError('An Infisical user or machine identity JWT is required') from None


def credential(profile):
    """Load only this project's private reference, rejecting expired or foreign user tokens."""
    if not profile.get('infisical'):
        raise ValueError('This project is registered for shell access; its Infisical app setup is not configured yet')
    path = Path(profile['infisical']['credential_ref']).expanduser()
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Credential reference must be a private regular file (chmod 600)')
    value = json.loads(path.read_text())
    if value['method'] == 'universal-auth':
        if not value.get('client_id') or not value.get('client_secret'):
            raise ValueError('Machine identity requires client_id and client_secret')
    elif value['method'] == 'user-token':
        check_token(profile, value['token'])
    else:
        raise ValueError('Supported auth methods: universal-auth, user-token')
    return value


def check_token(profile, token):
    """Require the configured organization/principal and at least five minutes of lifetime."""
    data = claims(token)
    config = profile['infisical']
    if data.get('organizationId', data.get('orgId')) != config['organization_id']:
        raise ValueError('Infisical token belongs to another organization')
    if data.get('userId', data.get('identityId')) != config['principal_id']:
        raise ValueError('Infisical token belongs to another user or machine identity')
    if data.get('exp', 0) < time.time() + 300:
        raise ValueError('This project needs an Infisical sign-in or credential refresh')
    return data
