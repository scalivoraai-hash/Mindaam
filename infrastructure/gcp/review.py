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
from deploy import release_gate


def packet(c, sha):
    staged = c.get_json(f'releases/{sha}/staging-verified.json')
    if not staged:
        raise Blocked('Complete real staging acceptance first')
    items = ('cloud_run','compute_livekit','postgresql','redis','storage','network','logging','other')
    value = {'sha':sha,'image':staged['image'],'reviewed_at':None,'owner_approved':False,
             'resource_metrics_evidence':staged['resource_metrics_evidence'],
             'costs':{scenario:{'assumptions':{'connected_user_hours':None,'media_publisher_hours':None,'media_receiver_hours':None,'internet_egress_gib':None,'api_requests':None},
                                'pricing_sources':[], 'usd':dict.fromkeys(items,None)} for scenario in ('idle','light')},
             'targets':{'preferred_light_usd':100,'warning_usd':125,'requires_new_approval_above_usd':150},
             'inventory':c.get_json('foundation.json'),
             'pricing_references':['https://cloud.google.com/run/pricing','https://cloud.google.com/compute/all-pricing',
                                   'https://cloud.google.com/sql/pricing','https://cloud.google.com/storage/pricing',
                                   'https://cloud.google.com/secret-manager/pricing','https://cloud.google.com/stackdriver/pricing'],
             'limitations':'WebSockets keep Cloud Run billed. Fixed caps are not a guaranteed bill ceiling. Credit is excluded. No 500/1000-user capacity assertion.'}
    return value


def save(c, sha, value):
    # Validate against real release evidence before writing the production gate object.
    staged = c.get_json(f'releases/{sha}/staging-verified.json')
    if not staged or value.get('resource_metrics_evidence') != staged['resource_metrics_evidence']:
        raise Blocked('Review must reference this release\'s actual measurements')
    if not c.get_json(f'releases/{sha}/metrics.json'):
        raise Blocked('Actual metrics evidence is missing')
    value['reviewed_at'] = int(time.time())
    old_get = c.get_json
    c.get_json = lambda key: value if key == f'releases/{sha}/release-review.json' else old_get(key)
    try:
        release_gate(c, staged['image'], sha)
    finally:
        c.get_json = old_get
    c.put_json(f'releases/{sha}/release-review.json', value)
    print('Reviewed cost evidence stored; production remains a separate explicit operation.')


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--project',required=True); p.add_argument('--sha',required=True); p.add_argument('--input')
    args=p.parse_args(); c=Cloud(args.project); c.require_project()
    if args.input:
        save(c,args.sha,json.loads(Path(args.input).read_text()))
    else:
        print(json.dumps(packet(c,args.sha),indent=2))
