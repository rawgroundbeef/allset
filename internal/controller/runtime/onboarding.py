"""Create one private project/provider binding through an explicit native flow."""

import json
import os
from pathlib import Path
import re
import subprocess
import uuid

import agent_auth
import github_auth
import repository_access
from profiles import credential, identifier, validate


def _atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def _read_private(path):
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Onboarding journal must be a private regular file owned by this user')
    return json.loads(path.read_text())


def _validate_journal(value, name, repository):
    stages = {'environment-intent', 'environment-created', 'environment-safe', 'profile-saved', 'complete'}
    if (not isinstance(value, dict) or value.get('version') != 1 or value.get('project') != name
            or value.get('repository') != repository or value.get('provider') != 'box'
            or value.get('stage') not in stages
            or not re.fullmatch('allset-' + re.escape(name) + r'-[0-9a-f]{10}', value.get('environment', ''))):
        raise ValueError('Onboarding journal is corrupt or belongs to another project')
    return value


def _scope_args(scope):
    return ['--org', scope]


def _has_environment(value, name):
    if isinstance(value, dict):
        if value.get('name') == name:
            return True
        return any(_has_environment(item, name) for item in value.values())
    if isinstance(value, list):
        return any(_has_environment(item, name) for item in value)
    return False


def _environment_is_safe(value, name):
    if isinstance(value, dict):
        if value.get('name') == name and value.get('safeForThirdParties', value.get('safe_for_third_parties')) is True:
            return True
        return any(_environment_is_safe(item, name) for item in value.values())
    if isinstance(value, list):
        return any(_environment_is_safe(item, name) for item in value)
    return False


def _account_identity(status):
    """Extract stable public account identity; never persist the changing status response."""
    values = {'id': [], 'email': []}
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = key.lower().replace('_', '')
                if normalized in ('accountid', 'userid') and isinstance(item, str):
                    values['id'].append(item)
                elif normalized in ('email', 'useremail', 'accountemail') and isinstance(item, str):
                    values['email'].append(item)
                elif isinstance(item, (dict, list)):
                    visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(status)
    identity = {key: items[0] for key, items in values.items() if items and items[0] and len(items[0]) <= 200}
    if not identity:
        raise ValueError('Box status did not expose a stable public account identity')
    return identity


def _providers(items):
    providers = {}
    for item in items or []:
        client = item.get('client') if isinstance(item, dict) else None
        expected = item.get('expected_account') if isinstance(item, dict) else None
        if client not in agent_auth.REMOTE_FILES or client in providers or not isinstance(expected, str) or not expected.strip():
            raise ValueError('Invalid private coding-client selection')
        providers[client] = {'account_email': expected.strip()}
    return providers


def _journal_providers(value):
    providers = value.get('providers') or {}
    if (not isinstance(providers, dict) or not providers or set(providers) - set(agent_auth.REMOTE_FILES)
            or any(not isinstance(item, dict) or set(item) != {'account_email'}
                   or not isinstance(item['account_email'], str) or not item['account_email'].strip()
                   for item in providers.values())):
        raise ValueError('Onboarding journal has invalid coding-client choices')
    return providers


def verify_provider_binding(controller, profile):
    binding = profile.get('provider_binding') or {}
    if not binding:
        return
    scope = binding.get('billing_scope')
    if scope: os.environ['BOX_ORG'] = scope
    actual = _account_identity(controller.box('status', *_scope_args(scope)))
    if actual != binding.get('account_identity'):
        raise ValueError('Active Box account does not match this project binding; no lifecycle mutation started')


def ensure_profile(controller, request):
    """Persist deliberate choices before compute; reconcile an unknown environment mutation."""
    project = request.get('project') or {}
    name = identifier(project.get('name'))
    if project.get('backend') != 'box' or not project.get('repository'):
        raise ValueError('Onboarding requires an explicit Box project and repository')
    target = controller.STATE / 'projects' / name / 'profile.json'
    if target.exists():
        existing = validate(_read_private(target))
        if existing['repository'] != project['repository']:
            raise ValueError('Existing private profile belongs to another repository')
        binding = agent_auth.config(controller, existing) or {}
        pending = []
        for client in existing.get('clients') or []:
            path = agent_auth.cache_path(controller, existing, client)
            cached = agent_auth.read_private(path) if path.exists() else {}
            if cached.get('needs_login') or not agent_auth.has_login(client, cached.get('contents')):
                pending.append(client)
        return existing, pending
    journal_path = controller.STATE / 'projects' / name / 'onboarding.json'
    journal = _validate_journal(_read_private(journal_path), name, project['repository']) if journal_path.exists() else None
    if journal and journal['stage'] in ('profile-saved', 'complete'):
        raise ValueError('Onboarding journal says the private profile exists, but it is missing')
    requested_providers = _providers(request.get('clients'))
    if journal:
        providers = _journal_providers(journal)
        if requested_providers and requested_providers != providers:
            raise ValueError('Onboarding retry conflicts with the recorded coding-client choices')
    else:
        providers = requested_providers
    if not providers:
        raise ValueError('Choose at least one coding client')

    personal_skills = journal.get('personal_skills') if journal else None
    if personal_skills is None:
        personal_skills = []
        raw_skills = input('Personal skill directories (comma-separated absolute paths, blank for none): ').strip()
        names = set()
        for raw in raw_skills.split(',') if raw_skills else []:
            path = Path(raw.strip()).expanduser()
            name_for_skill = identifier(path.name)
            if name_for_skill in names or not path.is_absolute() or path.is_symlink() or not (path / 'SKILL.md').is_file():
                raise ValueError('Personal skills require unique absolute directories containing SKILL.md')
            names.add(name_for_skill); personal_skills.append({'name': name_for_skill, 'path': str(path)})

    github = journal.get('github') if journal else None
    if not journal:
        print('Repository access is independent from model and Box accounts.', flush=True)
        github_login = input('GitHub CLI account login (leave blank for a public repository): ').strip()
        if github_login:
            github = {'provider': 'github-cli', 'account_login': github_login}
    if github:
        environment_for_github = github_auth.clean_environment()
        token = github_auth.run_native(['gh', 'auth', 'token', '--hostname', 'github.com',
                                        '--user', github['account_login']], env=environment_for_github)
        github_auth.verify_account('gh', {**environment_for_github, 'GH_TOKEN': token},
                                   github['account_login'], repository_access.github_repository(project['repository']))

    infisical = None
    if project.get('session_environment'):
        if journal and journal.get('infisical'):
            infisical = journal['infisical']
        else:
            print('This project declares scoped session secrets from Infisical.', flush=True)
            instance = input('Infisical HTTPS instance [https://app.infisical.com]: ').strip() or 'https://app.infisical.com'
            organization = input('Infisical organization ID: ').strip()
            project_id = input('Infisical project ID: ').strip()
            environment_name = input('Infisical environment slug: ').strip()
            principal = input('Infisical user or machine identity ID: ').strip()
            credential_ref = input('Absolute path to its private credential reference: ').strip()
            infisical = {'instance': instance, 'organization_id': organization, 'project_id': project_id,
                         'environment': environment_name, 'principal_id': principal,
                         'credential_ref': credential_ref}

    print('Box account and billing are independent from coding-client accounts.', flush=True)
    scope = journal.get('billing_scope') if journal else input('Box billing organization ID or name (including your personal organization): ').strip()
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', scope or ''):
        raise ValueError('Box billing scope requires an explicit organization ID or name')
    scope_args = _scope_args(scope)
    os.environ['BOX_ORG'] = scope
    try:
        try:
            status = controller.box('status', *scope_args)
        except Exception:
            raise ValueError('Box sign-in could not be verified for the selected billing scope') from None
    except Exception:
        print('Box sign-in is required. Complete the native browser flow for this billing scope.', flush=True)
        if subprocess.call([str(controller.BOX), '--no-update', 'login', *scope_args]):
            raise ValueError('Box sign-in did not complete') from None
        status = controller.box('status', *scope_args)
    limits = controller.box('limits', *scope_args)
    controller.check_allowance(limits, 60, reserved_seconds=0)
    account_identity = _account_identity(status)
    if journal and journal.get('account_identity') != account_identity:
        raise ValueError('Active Box account does not match the interrupted onboarding journal')
    print('Box identity: ' + (account_identity.get('email') or account_identity['id']), flush=True)
    print('Machine: small (half rate); auto-stop: at most 7200 seconds.', flush=True)
    environment = journal['environment'] if journal else 'allset-' + name + '-' + uuid.uuid4().hex[:10]
    agent_name = name + '-agents'
    agent_path = controller.STATE / 'agent-profiles' / agent_name / 'profile.json'
    agent_profile = {'version': 1, 'name': agent_name, 'providers': providers}
    if agent_path.exists() and _read_private(agent_path) != agent_profile:
        raise ValueError('Existing agent account binding conflicts with onboarding choices')
    profile = {'version': 2, 'name': name, 'aliases': project.get('aliases') or [],
               'repository': project['repository'], 'base': '', 'template': None,
               'box_environment': environment, 'setup_commands': [], 'services': [],
               'preview_service': '', 'coding_only': True, 'agent_profile': agent_name,
               'clients': sorted(providers), 'personal_skills': personal_skills, 'provider_binding': {
                   'provider': 'box', 'billing_scope': scope, 'environment': environment,
                   'safe_for_third_parties': True, 'account_identity': account_identity}}
    if github is not None:
        profile['github'] = github
    if infisical is not None:
        profile['infisical'] = infisical
    validate(profile)
    if infisical is not None:
        credential(profile)
    if not journal and input('Create this private project environment? [y/N]: ').strip().lower() not in ('y', 'yes'):
        raise ValueError('onboarding cancelled before provider mutation')

    if not journal:
        journal = {'version': 1, 'project': name, 'repository': project['repository'],
                   'provider': 'box', 'billing_scope': scope, 'environment': environment,
                   'account_identity': account_identity,
                   'providers': providers, 'personal_skills': personal_skills, 'github': github,
                   'infisical': infisical, 'environment_create_attempted': False,
                   'stage': 'environment-intent'}
        _atomic(journal_path, journal)
    if journal['stage'] == 'environment-intent':
        listing = controller.box('env', 'list', *scope_args)
        exists = _has_environment(listing, environment)
        if exists and not journal.get('environment_create_attempted'):
            raise ValueError('Generated Box environment name already exists; no environment was adopted')
        if not exists:
            journal['environment_create_attempted'] = True; _atomic(journal_path, journal)
            try:
                controller.box('env', 'new', environment, *scope_args)
            except (subprocess.TimeoutExpired, controller.BoxCommandError) as error:
                if not isinstance(error, subprocess.TimeoutExpired) and not error.result.get('timedOut'):
                    raise RuntimeError('Box environment creation failed; native response withheld') from None
                listing = controller.box('env', 'list', *scope_args)
                if not _has_environment(listing, environment):
                    raise RuntimeError('Box environment creation outcome is unknown; retry after inspecting the recorded environment') from None
        journal['stage'] = 'environment-created'; _atomic(journal_path, journal)
    if journal['stage'] == 'environment-created':
        try:
            changed = controller.box('env', 'set', environment, '--safe-for-third-parties', 'true', *scope_args)
        except Exception:
            raise RuntimeError('Box environment safety configuration failed; native response withheld') from None
        if not _environment_is_safe(changed, environment):
            listing = controller.box('env', 'list', *scope_args)
            if not _environment_is_safe(listing, environment):
                raise RuntimeError('Box did not verify that ambient credential injection is disabled')
        journal['stage'] = 'environment-safe'; _atomic(journal_path, journal)
    elif journal['stage'] == 'environment-safe':
        if not _environment_is_safe(controller.box('env', 'list', *scope_args), environment):
            raise RuntimeError('Recorded Box environment is no longer verified as safe; no compute mutation started')

    _atomic(agent_path, agent_profile)
    _atomic(target, profile)
    journal['stage'] = 'profile-saved'; _atomic(journal_path, journal)
    return profile, sorted(providers)
