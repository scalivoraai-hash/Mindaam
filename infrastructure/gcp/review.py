from release_policy import profile, evidence_name, review_name, BETA, POLICY
"""Create a review packet or validate/persist reviewed cost data. Contains no secrets.

The deployment operator completes the price/usage review from actual inventory,
Cloud Monitoring and current provider rates; the account owner never edits app code.
An absent estimate is deliberately null, never an invented $0 or a deployment PASS.
"""
import argparse
import json
import time
from pathlib import Path
from common import Cloud, Blocked, SETTINGS
from deploy import release_gate, optional_secrets
from readiness import ready_service


def inventory(c):
    sql = c.gc('sql', 'instances', 'describe', 'mindaam-postgres'); c.owned(sql, 'PostgreSQL')
    vm = c.gc('compute', 'instances', 'describe', 'mindaam-media', '--zone=' + c.zone); c.owned(vm, 'media VM')
    run = ready_service(c, 'mindaam-staging')
    template = run.get('spec', {}).get('template', {})
    databases = c.gc('sql','databases','list','--instance=mindaam-postgres')
    backups = c.gc('sql','backups','list','--instance=mindaam-postgres','--limit=5')
    return {'databases':[{'name':row.get('name')} for row in databases], 'recent_backups':[{k:row.get(k) for k in ('id','status','type','startTime','endTime')} for row in backups], 'project': c.project, 'region': c.region, 'foundation': c.get_json('foundation.json'),
            'sql': {k: sql.get(k) for k in ('name', 'region', 'databaseVersion', 'settings')},
            'vm': {k: vm.get(k) for k in ('name', 'machineType', 'disks', 'networkInterfaces')},
            'staging': {'name': run.get('metadata', {}).get('name'), 'annotations': run.get('metadata', {}).get('annotations'),
                        'template_annotations': template.get('metadata', {}).get('annotations'),
                        'containers': [{'image': x.get('image'), 'resources': x.get('resources')} for x in template.get('spec', {}).get('containers', [])]},
            'production_limits': {'max_instances': SETTINGS['production_max_instances'],
                                  'cpu': SETTINGS['cloud_run_cpu'], 'memory': SETTINGS['cloud_run_memory']}}


def packet(c, sha):
    staged = c.get_json(f'releases/{sha}/{evidence_name()}')
    if not staged:
        raise Blocked('Complete real staging acceptance first')
    configured = {env: optional_secrets(c, env) for env in ('staging', 'production')}
    items = ('cloud_run','compute_livekit','postgresql','redis','storage','network','logging','other')
    value = {'sha':sha,'image':staged['image'],'reviewed_at':None,'owner_approved':False,'pricing_date':None,
             'resource_metrics_evidence':staged['resource_metrics_evidence'],
             'costs':{scenario:{'assumptions':{'connected_user_hours':None,'media_publisher_hours':None,'media_receiver_hours':None,'internet_egress_gib':None,'api_requests':None},
                                'pricing_sources':[], 'usd':dict.fromkeys(items,None)} for scenario in ('idle','light')},
             'targets':{'preferred_light_usd':100,'warning_usd':125,'requires_new_approval_above_usd':150},
             'inventory':inventory(c),
             'optional_providers': {env: {provider: all(key in configured[env] for key in keys)
                 for provider, keys in {'stripe':['STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','STRIPE_SUBSCRIPTION_WEBHOOK_SECRET'],
                 'smtp':['SMTP_HOST','SMTP_PORT','SMTP_USERNAME','SMTP_PASSWORD','SMTP_FROM'],
                 'google_login':['GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET']}.items()} for env in ('staging','production')},
             'pricing_references':['https://cloud.google.com/run/pricing','https://cloud.google.com/compute/all-pricing',
                                   'https://cloud.google.com/sql/pricing','https://cloud.google.com/storage/pricing',
                                   'https://cloud.google.com/secret-manager/pricing','https://cloud.google.com/stackdriver/pricing'],
             'limitations':'WebSockets keep Cloud Run billed. Fixed caps are not a guaranteed bill ceiling. Credit is excluded. No 500/1000-user capacity assertion.'}
    value.update({'profile':profile(), 'deferred':POLICY['deferred'] if profile()==BETA else {}, 'payment_actions_enabled':False, 'security_review':c.get_json(f'releases/{sha}/security-review.json')})
    return value


def save(c, sha, value):
    # Validate against real release evidence before writing the production gate object.
    staged = c.get_json(f'releases/{sha}/{evidence_name()}')
    if not staged or value.get('resource_metrics_evidence') != staged['resource_metrics_evidence']:
        raise Blocked('Review must reference this release\'s actual measurements')
    if not c.get_json(f'releases/{sha}/metrics.json'):
        raise Blocked('Actual metrics evidence is missing')
    value['inventory'] = inventory(c)
    value['reviewed_at'] = int(time.time())
    old_get = c.get_json
    c.get_json = lambda key: value if key == f'releases/{sha}/{review_name()}' else old_get(key)
    try:
        release_gate(c, staged['image'], sha)
    finally:
        c.get_json = old_get
    if sum(value['costs']['light']['usd'].values()) >= SETTINGS['budget_usd']:
        print('Warning: light-use estimate is at or above $125/month; preferred target is below $100.')
    c.put_json(f'releases/{sha}/{review_name()}', value)
    print('Reviewed cost evidence stored; production remains a separate explicit operation.')


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--project',required=True); p.add_argument('--sha',required=True); p.add_argument('--input')
    args=p.parse_args(); c=Cloud(args.project); c.require_project()
    if args.input:
        save(c,args.sha,json.loads(Path(args.input).read_text()))
    else:
        print(json.dumps(packet(c,args.sha),indent=2))
