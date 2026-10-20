"""Validate pinned third-party binaries against rendered configs, without GCP credentials."""
import json
import subprocess
import tempfile
import time
from pathlib import Path
from common import SETTINGS
from render import caddy_config, livekit_config, compose_config


def run(*args):
    subprocess.run(args, check=True)


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory); path.chmod(0o755)
        (path/'caddy.json').write_text(json.dumps(caddy_config('https://mindaam-production-validation.run.app')))
        (path/'livekit.json').write_text(json.dumps(livekit_config({'validation': 'x'*40})))
        (path/'compose.json').write_text(json.dumps(compose_config()))
        run('docker','compose','-f',str(path/'compose.json'),'config','--quiet')
        run('docker','run','--rm','-v',str(path)+':/test:ro',SETTINGS['images']['caddy'],'validate','--config','/test/caddy.json')
        try:
            run('docker','run','-d','--name','mindaam-config-check','-v',str(path)+':/test:ro',SETTINGS['images']['livekit'],'--config','/test/livekit.json')
            time.sleep(5)
            state=json.loads(subprocess.check_output(['docker','inspect','mindaam-config-check']))[0]['State']
            if not state['Running']:
                run('docker','logs','mindaam-config-check'); raise RuntimeError('Pinned LiveKit rejected configuration')
        finally:
            subprocess.run(['docker','rm','-f','mindaam-config-check'],check=False,stdout=subprocess.DEVNULL)


if __name__=='__main__': main()
