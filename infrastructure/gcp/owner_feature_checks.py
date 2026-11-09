"""Read-only owner acceptance of the staged admin modules. No account data exports."""
from uuid import UUID
from common import Blocked

REQUIRED = ('property_economy_read', 'movement_configuration_read',
            'user_directory_read', 'user_detail_tabs_read')


def require(value, category):
    if not value:
        raise Blocked('Staging owner feature check failed: ' + category)


def verify(call, user_id):
    user_id = str(UUID(user_id))
    read = lambda label, path: call(label, path, 200, read_json=True)
    movement = read('movement_settings', '/api/super-admin/movement')
    require(isinstance(movement, dict), 'movement_response')
    bounds = movement.get('bounds', {})
    require(all(isinstance(bounds.get(k), list) and len(bounds[k]) == 2
                and bounds[k][1] == 100 for k in ('walk', 'run')), 'movement_bounds')
    speeds = movement.get('speeds', {})
    require(all(isinstance(speeds.get(k), (int, float)) for k in ('walk', 'run'))
            and 0 < speeds['walk'] <= speeds['run'] <= 100, 'movement_values')

    coverage = read('property_coverage', '/api/properties/admin/coverage')
    require(isinstance(coverage, list) and bool(coverage), 'property_coverage')
    require(all(isinstance(row, dict) and isinstance(row.get('city'), str)
                and isinstance(row.get('eligible'), int) and row['eligible'] > 0
                and isinstance(row.get('registered'), int)
                and row['registered'] >= row['eligible'] for row in coverage), 'property_inventory_gap')
    require(len({row['city'] for row in coverage}) == len(coverage), 'duplicate_city')
    economy = read('property_economy', '/api/properties/admin/overview')
    fields = ('registered', 'available', 'owned', 'owners', 'claims_xp', 'resales_xp', 'pending')
    require(isinstance(economy, dict) and all(type(economy.get(k)) is int and economy[k] >= 0
                                            for k in fields), 'property_statistics')
    require(economy['registered'] == economy['available'] + economy['owned']
            and economy['registered'] >= sum(row['registered'] for row in coverage), 'property_totals')

    directory = read('user_directory', '/api/super-admin/directory?q=' + user_id + '&limit=1')
    require(isinstance(directory, dict) and isinstance(directory.get('items'), list)
            and len(directory['items']) == 1 and directory['items'][0].get('id') == user_id,
            'user_directory')
    for tab in ('overview', 'wallet', 'properties', 'events', 'activity'):
        detail = read('user_' + tab, '/api/super-admin/users/' + user_id + '/detail?tab=' + tab)
        require(isinstance(detail, dict) and detail.get('user', {}).get('id') == user_id
                and detail.get('tab') == tab, 'user_detail_identity')
        if tab == 'overview':
            kpis = detail.get('kpis', {})
            require(all(type(kpis.get(k)) is int for k in ('Spendable XP', 'Pulse Credits',
                        'Owned properties', 'Hosted events', 'Active days')), 'user_kpis')
        else:
            require(isinstance(detail.get('items'), list) and type(detail.get('total')) is int
                    and detail['total'] >= 0, 'user_detail_records')
        if tab == 'wallet':
            require(all(type(detail.get(k)) is int and detail[k] >= 0
                        for k in ('xp', 'credits', 'purchased_available')), 'wallet_read')
    return dict.fromkeys(REQUIRED, True)


def require_evidence(checks):
    require(all(checks.get(k) is True for k in REQUIRED), 'missing_authenticated_evidence')
