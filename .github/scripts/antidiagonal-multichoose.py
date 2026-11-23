"""Verification for the two SumAntidiagonalTuple modules and their direct callers."""
import concurrent.futures
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

root = Path.cwd()
report = Path(os.environ['BENCH_OUTPUT'])
report.mkdir(parents=True, exist_ok=True)
mods = ['Formalism.PeriodIntegrals.SumAntidiagonalTuple',
        'Formalism.PeriodIntegrals.OrbitalBoundsConclusion.SumAntidiagonalTuple']
clients = ['Formalism.PeriodIntegrals.UnitaryGroupMassFormula.' + name
           for name in ['BaseLengthBound.Assembly', 'PoleLengthBound.StepsOf']]
paths = [Path('src', *name.split('.')).with_suffix('.lean') for name in mods]
imports = re.compile(r'^(?:(?:public|meta) +)*import +(?:all +)?([\w.«»\']+)', re.M)

def git(*args):
    return subprocess.check_output(['git', *args])

def run_logged(label, cmd):
    start = time.monotonic()
    path = report / (label + '.log')
    with path.open('w') as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    elapsed = round(time.monotonic() - start, 3)
    print(path.read_text()[-2400:], flush=True)
    result.check_returncode()
    return elapsed

def deps():
    needed, todo = set(), clients.copy()
    while todo:
        name = todo.pop()
        path = Path('src', *name.split('.')).with_suffix('.lean')
        if name in needed or not path.exists():
            continue
        needed.add(name)
        todo.extend(imports.findall(path.read_text()))
    return needed.difference(mods, clients)

def restore_deps(needed):
    toolchain = Path('lean-toolchain').read_text().strip()
    pins = json.loads(Path('scripts/cache-baselines.json').read_text())['toolchains'][toolchain]['baseline']
    url = 'https://rh-cache.taucetiproject.org'
    def fetch(address):
        return subprocess.check_output(['curl','-fsSL','--retry','4','--max-time','90', address])
    data = fetch(f"{url}/bootstrap/{pins['revision']}/modules.jsonl.gz")
    assert hashlib.sha256(data).hexdigest() == pins['manifest_sha256']
    lines = gzip.decompress(data).splitlines()
    manifest = json.loads(lines[0])
    assert manifest['toolchain'] == toolchain
    assert manifest['manifest_sha256'] == hashlib.sha256(Path('lake-manifest.json').read_bytes()).hexdigest()
    assert manifest['lakefile_sha256'] == hashlib.sha256(Path('lakefile.toml').read_bytes()).hexdigest()
    rows = [row for line in lines[1:] if (row := json.loads(line))[0] in needed]
    assert {r[0] for r in rows} == needed
    cache = report.parent / 'rh-consumer-cache'
    store = cache / 'artifacts'
    store.mkdir(parents=True,exist_ok=True)
    def download(row):
        _, _, name, sha = row
        payload = fetch(f"{url}/artifacts/leanprover-community/riemann-hypothesis/{name[:-5]}.art")
        assert hashlib.sha256(payload).hexdigest() == sha
        (store / name).write_bytes(payload)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(download, rows))
    spec = importlib.util.spec_from_file_location('restore', 'scripts/restore-cache.py')
    restore = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restore)
    jobs = restore.restore_jobs(root,cache,rows)
    for job in jobs:
        for directory in job['base']:
            Path(directory).mkdir(parents=True,exist_ok=True)
    leantar = Path(subprocess.check_output(['lean','--print-prefix'],text=True).strip()) / 'bin/leantar'
    subprocess.run([leantar,'--jobs','4','-f','-x','-j','-'],input=json.dumps(jobs),text=True,check=True)
    shutil.rmtree(cache)
    print(f'Restored {len(rows)} pinned upstream dependencies. Lake checks their build traces.', flush=True)

def main():
    base, head = os.environ['BASE'], os.environ['HEAD']
    assert git('rev-parse','HEAD').decode().strip() == head
    assert git('rev-parse','HEAD^').decode().strip() == base
    assert set(git('diff','--name-only',base,head).decode().splitlines()) == {str(p) for p in paths}
    assert git('-C','.lake/packages/mathlib','rev-parse','HEAD').decode().strip() == os.environ['MATHLIB']
    sources = {v:[git('show',f'{sha}:{p}') for p in paths] for v,sha in [('before',base),('after',head)]}
    rows = []
    for i, order in enumerate([('before','after'),('before','after'),('after','before'),('before','after')]):
        for side in order:
            for mod, p, source in zip(mods,paths,sources[side]):
                p.write_bytes(source)
                rel = Path(*mod.split('.'))
                for d in ['.lake/build/lib/lean','.lake/build/ir']:
                    for f in (Path(d) / rel.parent).glob(rel.name+'.*'):
                        if f.is_file():
                            f.unlink()
            elapsed = run_logged(f'{i}-{side}',['lake','--no-cache','build',*['+'+m for m in mods]])
            row = {'run':i,'side':side,'wall_seconds':elapsed,'artifacts':{}}
            for mod,source in zip(mods,sources[side]):
                art = Path('.lake/build/lib/lean',*mod.split('.'))
                row['artifacts'][mod] = {'direct':len(imports.findall(source.decode())),
                                         'olean':art.with_suffix('.olean').stat().st_size,
                                         'private':art.with_suffix('.olean.private').stat().st_size}
            print(json.dumps(row),flush=True)
            rows.append(row)
            (report/'measurements.json').write_text(json.dumps(rows,indent=2))
    print({s:statistics.median(r['wall_seconds'] for r in rows if r['side']==s and r['run']>0) for s in ('before','after')})
    assert not git('diff','--name-only')
    check = report / 'AntidiagonalInterface.lean'
    check.write_text('import '+mods[1]+'\nexample : PI.SumAntidiagonalTuple := sum_antidiagonalTuple\n#print axioms sum_antidiagonalTuple\n')
    run_logged('interface',['lake','env','lean',str(check)])
    restore_deps(deps())
    run_logged('consumers',['lake','--no-cache','build',*['+'+m for m in clients]])

if __name__ == '__main__':
    main()
