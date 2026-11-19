"""Supabase server-side REST access. Never expose the secret key in frontend code."""
import os
import requests


def env(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing secret: {name}')
    return value


def _call(method, path, **kwargs):
    key = env('SUPABASE_KEY')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    # Legacy service_role keys are JWTs; modern sb_secret keys are not JWTs.
    if not key.startswith('sb_secret_'):
        headers['Authorization'] = 'Bearer ' + key
    headers.update(kwargs.pop('headers', {}))
    resp = requests.request(method, env('SUPABASE_URL').rstrip('/') + '/rest/v1/' + path,
                            headers=headers, timeout=25, **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.content else None


def read_state():
    data = _call('GET', 'trader_state?id=eq.1&select=state')
    return data[0]['state'] if data else None


def write_state(state):
    _call('POST', 'trader_state?on_conflict=id', json={'id': 1, 'state': state},
          headers={'Prefer': 'resolution=merge-duplicates,return=minimal'})
