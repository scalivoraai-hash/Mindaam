"""Check documented command/flag availability with the installed SDK; never calls GCP."""
import os
import re
import subprocess

COMMANDS={
 'sql operations wait':['--timeout'],
 'sql operations list':['--instance'],
 'sql users set-password':['--password','--flags-file'],
 'run jobs deploy':['--set-cloudsql-instances','--set-secrets','--task-timeout'],
 'run services replace':['--region'],
 'artifacts repositories set-cleanup-policies':['--policy','--no-dry-run'],
 'storage buckets create':['--uniform-bucket-level-access','--public-access-prevention'],
 'storage buckets update':['--versioning','--lifecycle-file','--update-labels'],
 'compute instances create':['--private-network-ip','--shielded-secure-boot','--metadata-from-file'],
 'billing budgets create':['--filter-projects','--credit-types-treatment','--threshold-rule'],
 'iam workload-identity-pools providers create-oidc':['--attribute-mapping','--attribute-condition'],
}
for command,flags in COMMANDS.items():
    output=subprocess.check_output(['gcloud',*command.split(),'--help'],text=True,env={**os.environ,'CLOUDSDK_CORE_DISABLE_PROMPTS':'1','PAGER':'cat','TERM':'dumb'})
    output=re.sub(r'\x1b\[[0-9;]*m','',output)
    while '\b' in output:
        output=re.sub(r'.\x08','',output)
    normalized=output.replace('--[no-]','--').replace('--no-','--')
    for flag in flags:
        assert flag.replace('--no-','--') in normalized, f'Unsupported SDK flag {command}: {flag}'
    print('CLI syntax supported:',command)
