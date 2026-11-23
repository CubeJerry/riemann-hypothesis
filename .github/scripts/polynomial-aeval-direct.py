"""Bounded stock-Lake verification; no full Main build or Comparator claim."""
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
removed = ['Lemmata.PowerApplication.PowApp', 'Lemmata.PowerMembership.PowMem']
clients = ['ReciprocityTheory.ReductiveGroups.DiscreteSeries.TensorRepresentations.DecompA',
           'Formalism.SharpRestriction.LevelLetterCocycles.DvrLatticeRank.AevalMemOfStable']
mods = removed + clients
paths = [Path('src', *name.split('.')).with_suffix('.lean') for name in mods]
def header_imports(source):
    """Read only the header, skipping nested block comments and line comments."""
    def lines():
        line, depth, i = [], 0, 0
        while i < len(source):
            if source.startswith('/-', i):
                if not depth: line.append(' ')
                depth += 1
                i += 2
            elif depth and source.startswith('-/', i):
                depth -= 1
                i += 2
            elif not depth and source.startswith('--', i):
                newline = source.find('\n', i)
                i = len(source) if newline < 0 else newline
            elif source[i] == '\n':
                yield ''.join(line)
                line = []
                i += 1
            else:
                if not depth: line.append(source[i])
                i += 1
        if line: yield ''.join(line)
    result = []
    name = r"(?:[\w']+|«[^»]+»)(?:\.(?:[\w']+|«[^»]+»))*"
    for line in lines():
        line = line.strip()
        while re.match(r'^(module|prelude)\b', line):
            line = re.sub(r'^(module|prelude)\b', '', line, count=1).strip()
        if not line: continue
        match = re.fullmatch(r'(?:(?:public|meta)\s+)*import\s+(?:all\s+)?(.+)', line)
        if not match: break
        imported = match.group(1)
        assert not re.sub(name, '', imported).strip(), imported
        result.extend(re.findall(name, imported))
    return result

INTERFACE_COMPARISON = 'import Lean\n\nopen Lean\n\ndef main (args : List String) : IO Unit := do\n  let [oldFile, newFile] := args | throw <| IO.userError "two compiled module paths required"\n  let (old, _) ← readModuleData oldFile\n  let (new, _) ← readModuleData newFile\n  let oldPublic := old.constants.filter fun c => !isPrivateName c.name\n  let newPublic := new.constants.filter fun c => !isPrivateName c.name\n  unless oldPublic.size == newPublic.size do\n    throw <| IO.userError s!"public declaration count changed: {oldPublic.size} to {newPublic.size}"\n  for decl in oldPublic do\n    let some other := newPublic.find? (·.name == decl.name)\n      | throw <| IO.userError s!"missing {decl.name}"\n    unless decl.levelParams == other.levelParams && decl.type.equal other.type do\n      throw <| IO.userError s!"type changed: {decl.name}"\n  IO.println s!"identical compiled public names, universe parameters and types: {oldPublic.size}"\n  IO.println "Import changes are checked separately against the source diff."\n'

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
        todo.extend(header_imports(path.read_text()))
    return needed.difference(mods)

def restore_deps(needed):
    assert len(needed) <= 500 and not needed.intersection(mods)
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
    assert manifest['map_sha256'] == pins['map_sha256']
    rows = [row for line in lines[1:] if (row := json.loads(line))[0] in needed]
    assert {r[0] for r in rows} == needed
    if subprocess.run(['git','cat-file','-e',pins['revision']], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        subprocess.run(['git','fetch','--no-tags','--depth=1',
                        'https://github.com/leanprover-community/riemann-hypothesis.git',
                        pins['revision']],check=True)
    assert git('rev-parse',pins['revision']+':src').decode().strip() == manifest['source_tree']
    source_blobs = {}
    for name in sorted(needed):
        path = str(Path('src',*name.split('.')).with_suffix('.lean'))
        blobs = [git('rev-parse',f'{ref}:{path}').decode().strip()
                 for ref in [pins['revision'],os.environ['BASE'],os.environ['HEAD']]]
        assert len(set(blobs)) == 1, (path,blobs)
        assert git('hash-object',path).decode().strip() == blobs[0]
        source_blobs[name] = blobs[0]
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
    (report/'dependency-restore.json').write_text(json.dumps({'pins':pins,'header':manifest,
        'artifacts':rows,'source_blobs':source_blobs,'target_artifacts_restored':False},indent=2))

def set_sources(sources):
    for name,path in zip(mods,paths):
        if name in sources:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(sources[name])
        else:
            path.unlink(missing_ok=True)

def clear_outputs():
    for name in mods:
        rel = Path(*name.split('.'))
        for directory in ['.lake/build/lib/lean','.lake/build/ir']:
            for f in (Path(directory)/rel.parent).glob(rel.name+'.*'):
                if f.is_file() or f.is_symlink():
                    f.unlink()

def source_counts(active):
    roots = [Path('src'),Path('.lake/packages/mathlib')] + sorted(
        p for p in Path('.lake/packages').iterdir() if p.is_dir() and p.name != 'mathlib')
    memo = {}
    def closure(start):
        seen,todo = set(),list(start)
        while todo:
            name = todo.pop()
            if name in seen: continue
            seen.add(name)
            if name not in memo:
                rel = Path(*name.split('.')).with_suffix('.lean')
                path = next((p/rel for p in roots if (p/rel).is_file()),None)
                memo[name] = header_imports(path.read_text()) if path else []
            todo.extend(memo[name])
        return seen
    per_module = {name:{'direct_imports':len(header_imports(source.decode())),
                        'source_mathlib_closure':sum(n == 'Mathlib' or n.startswith('Mathlib.')
                                                    for n in closure([name]))}
                  for name,source in active.items()}
    return {'modules':per_module,'direct_imports':sum(v['direct_imports'] for v in per_module.values()),
            'source_mathlib_closure':sum(n == 'Mathlib' or n.startswith('Mathlib.')
                                        for n in closure(active))}

def interface(side):
    declarations = ['ReciprocityTheory.ChartRestriction.DS.dc_aeval_eigen',
                    'ReciprocityTheory.ChartRestriction.DS.dc_aeval_mem',
                    'Formalism.MainNotions.N.Ln34.UniversalLiftFrames.aeval_mem_of_stable']
    check = report/'PolynomialAevalInterface.lean'
    check.write_text('\n'.join('import '+m for m in clients)+'\n'+
        '\n'.join('#check '+name+'\n#print axioms '+name for name in declarations)+'\n')
    label = 'interface-'+side
    run_logged(label,['lake','env','lean',str(check)])
    log = (report/(label+'.log')).read_text()
    result = {}
    for name in declarations:
        match = re.search(re.escape("'"+name+"'")+r' depends on axioms:\s*\[([^\]]*)\]',log)
        if match:
            axioms = {x.strip() for x in match.group(1).split(',') if x.strip()}
        else:
            assert "'"+name+"' does not depend on any axioms" in log
            axioms = set()
        assert axioms <= {'propext','Classical.choice','Quot.sound'},(name,axioms)
        result[name] = sorted(axioms)
    (report/('axioms-'+side+'.json')).write_text(json.dumps(result,indent=2))
    if os.environ.get('EXTRA_INTERFACE_PROBE'):
        run_logged('extra-interface-'+side,['lake','env','lean',os.environ['EXTRA_INTERFACE_PROBE']])
    comparison = report/'CheckConsumerInterface.lean'
    comparison.write_text(INTERFACE_COMPARISON)
    for name in clients:
        relative = Path(*name.split('.')).with_suffix('.olean')
        current = Path('.lake/build/lib/lean')/relative
        before = report/'before-public'/relative
        if side == 'before':
            before.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(current,before)
        else:
            run_logged('compiled-interface-'+name.split('.')[-1],
                       ['lake','env','lean','--run',str(comparison),str(before),str(current)])

def main():
    base, head = os.environ['BASE'], os.environ['HEAD']
    assert git('rev-parse','HEAD').decode().strip() == head
    assert git('rev-parse','HEAD^').decode().strip() == base
    assert not git('status','--porcelain','--untracked-files=no')
    expected = {str(p):'D' if m in removed else 'M' for m,p in zip(mods,paths)}
    changes = {line.split('\t')[1]:line.split('\t')[0]
               for line in git('diff','--no-renames','--name-status',base,head).decode().splitlines()}
    assert changes == expected,(changes,expected)
    protected = {}
    for path in ['src/Challenge.lean','src/Statements.lean','comparator.json',
                 'lean-toolchain','lake-manifest.json','lakefile.toml']:
        before,after = git('show',f'{base}:{path}'),git('show',f'{head}:{path}')
        assert before == after,path
        protected[path] = hashlib.sha256(after).hexdigest()
    assert git('-C','.lake/packages/mathlib','rev-parse','HEAD').decode().strip() == os.environ['MATHLIB']
    package_heads = {}
    manifest = json.loads(Path('lake-manifest.json').read_text())
    for package in manifest['packages']:
        assert package['type'] == 'git',('unsupported unpinned dependency',package['name'])
        path = Path('.lake/packages')/package['name']
        actual = git('-C',str(path),'rev-parse','HEAD').decode().strip()
        assert actual == package['rev'],(package['name'],actual,package['rev'])
        package_heads[package['name']] = actual
    for package in Path('.lake/packages').iterdir():
        if (package/'.git').exists():
            assert not git('-C',str(package),'status','--porcelain','--untracked-files=no'),package
    for key,value in {'LEAN_NUM_THREADS':'1','LEAN_ABORT_ON_PANIC':'1',
                      'LAKE_ARTIFACT_CACHE':'false','LAKE_RESTORE_ARTIFACTS':'false'}.items():
        assert os.environ.get(key) == value,key
    version = subprocess.check_output(['lean','--version'],text=True).strip()
    assert 'commit '+os.environ['LEAN_COMMIT'] in version and 'Release' in version,version
    identity = {'base':base,'head':head,'mathlib':os.environ['MATHLIB'],'lean':version,
                'lake':subprocess.check_output(['lake','--version'],text=True).strip(),
                'protected_sha256':protected,'package_heads':package_heads,
                'full_Main_Challenge_build':'NOT RUN','comparator':'NOT RUN'}
    (report/'identity.json').write_text(json.dumps(identity,indent=2))
    (report/'source.patch').write_bytes(git('diff','--no-ext-diff',base,head))
    sources = {'before':{m:git('show',f'{base}:{p}') for m,p in zip(mods,paths)},
               'after':{m:git('show',f'{head}:{p}') for m,p in zip(mods,paths) if m in clients}}
    for side,contents in sources.items():
        for m,source in contents.items():
            target = report/'sources'/side/Path(*m.split('.')).with_suffix('.lean')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source)
    rows,counts,needed = [],{},set()
    try:
        for side in ['before','after']:
            set_sources(sources[side])
            counts[side] = source_counts(sources[side])
            needed.update(deps())
        (report/'imports.json').write_text(json.dumps(counts,indent=2))
        clear_outputs()
        restore_deps(needed)
        command = ['lake','--no-cache','--rehash','build',*['+'+m for m in clients]]
        for i,order in enumerate([('before','after'),('before','after'),('after','before'),('before','after')]):
            for side in order:
                set_sources(sources[side])
                clear_outputs()
                label = f'{i}-{side}'
                elapsed = run_logged(label,command)
                log = re.sub(r'\x1b\[[0-9;]*m','',(report/(label+'.log')).read_text())
                assert 'Restored ' not in log
                built = set(re.findall(r'\bBuilt\s+([^\s(:]+)',log))
                active = set(sources[side])
                assert active <= built,(active,built)
                if i: assert not built-active,('unexpected measured dependency build',built-active)
                row = {'run':i,'warmup':i==0,'side':side,'command':command,'wall_seconds':elapsed,
                       'built_modules':sorted(built),'artifacts':{}}
                for m in sources[side]:
                    art = Path('.lake/build/lib/lean',*m.split('.'))
                    assert art.with_suffix('.olean').is_file(),m
                    row['artifacts'][m] = {key:art.with_suffix(suffix).stat().st_size
                                          if art.with_suffix(suffix).is_file() else None
                        for key,suffix in [('olean','.olean'),('private','.olean.private'),('server','.olean.server')]}
                row['unit_artifacts'] = {key:sum(a[key] or 0 for a in row['artifacts'].values())
                                         for key in ['olean','private','server']}
                rows.append(row)
                print(json.dumps(row),flush=True)
                (report/'measurements.json').write_text(json.dumps(rows,indent=2))
                if i == 0: interface(side)
        assert not git('diff','--name-only')
        assert not git('ls-files','--others','--exclude-standard','--','src')
        for m in clients:
            run_logged('leanchecker-'+m.split('.')[-1],['lake','env','leanchecker','--verbose',m])
        summary = {'imports':counts,'restored_project_dependencies':len(needed),
                   'scope':'Four modules before; two after. Warm unchanged dependencies.',
                   'full_Main_Challenge_build':'NOT RUN','comparator':'NOT RUN'}
        for side in ['before','after']:
            measured = [r for r in rows if r['side']==side and not r['warmup']]
            times = [r['wall_seconds'] for r in measured]
            summary[side] = {'wall_seconds':times,'median_wall_seconds':statistics.median(times),
                             'artifacts':measured[-1]['artifacts'],'unit_artifacts':measured[-1]['unit_artifacts']}
        (report/'summary.json').write_text(json.dumps(summary,indent=2))
        print('SUMMARY_JSON '+json.dumps(summary,sort_keys=True),flush=True)
        write_summary(summary)
    finally:
        set_sources(sources['after'])

def write_summary(summary):
    counts = summary['imports']
    text = '# Polynomial-evaluation changed-unit verification\n\n'
    text += '| Metric | Before | After |\n|---|---:|---:|\n'
    text += f"| Median command seconds | {summary['before']['median_wall_seconds']} | {summary['after']['median_wall_seconds']} |\n"
    for key in ['direct_imports','source_mathlib_closure']:
        text += f"| {key} | {counts['before'][key]} | {counts['after'][key]} |\n"
    for key in ['olean','private','server']:
        text += f"| Unit {key} bytes | {summary['before']['unit_artifacts'][key]} | {summary['after']['unit_artifacts'][key]} |\n"
    text += '\nOne warm-up per revision, then three pairs in AB, BA, AB order. Stock Lean, one thread. Both consumers replayed with stock leanchecker.\n'
    text += '\n**Bounded changed-unit diagnostic only. Full `lake build Main Challenge` and `lake comparator`: NOT RUN.**\n'
    (report/'summary.md').write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as stream: stream.write(text)

if __name__ == '__main__':
    main()

