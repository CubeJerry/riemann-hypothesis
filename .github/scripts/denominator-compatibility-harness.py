"""Lean 4.36 compatibility verification of the two changed modules only.

No direct consumers, full Main/Challenge build, or Comparator run are included.
"""
import hashlib
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
removed = []
changed = ['Lemmata.GeneralBFactThirdBisAlt.Imports',
           'Lemmata.GeneralBFactSecondBisAlt.Imports']
verified_modules = changed.copy()
mods = removed + verified_modules
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
    needed, todo = set(), verified_modules.copy()
    while todo:
        name = todo.pop()
        path = Path('src', *name.split('.')).with_suffix('.lean')
        if name in needed or not path.exists():
            continue
        needed.add(name)
        todo.extend(header_imports(path.read_text()))
    return needed.difference(mods)

def restore_deps(needed):
    """The two changed modules have no project ancestors on this exact old lane."""
    assert not needed, ('unexpected project ancestor in two-module compatibility scope', sorted(needed))
    receipt = {
        'scope':'two changed modules',
        'reason':'no project ancestors; no project-cache manifest or artifact downloaded',
        'pins':None,'header':None,'artifacts':[],'source_blobs':{},
        'project_import_graph':{name:[] for name in verified_modules},
        'direct_rejections':{},'rejected_cache_modules':{},
        'project_dependencies':0,'restored_project_dependencies':0,
        'fresh_project_dependencies':0,'target_artifacts_restored':False,
        'excluded_outputs_cleared':True,'project_cache_downloaded':False,
    }
    (report/'dependency-restore.json').write_text(json.dumps(receipt,indent=2))
    print('Two changed modules: zero project ancestors; skipped all project-cache downloads.',flush=True)
    return receipt


def set_sources(sources):
    for name,path in zip(mods,paths):
        if name in sources:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(sources[name])
        else:
            path.unlink(missing_ok=True)

def clear_outputs(selected=None):
    for name in mods if selected is None else selected:
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
                                        for n in closure(active)),
            'changed_direct_imports':sum(per_module[m]['direct_imports'] for m in changed),
            'changed_source_mathlib_closure':sum(n == 'Mathlib' or n.startswith('Mathlib.')
                                                for n in closure(changed))}

def interface(side):
    declarations = ['Bl.general_b_fact_third_bis_other.goal1',
                    "Bl.general_b_fact_second''''''''.goal1"]
    check = report/'DenominatorInterface.lean'
    check.write_text('\n'.join('import '+m for m in verified_modules)+'\n'+
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
    comparison = report/'CheckChangedInterface.lean'
    comparison.write_text(INTERFACE_COMPARISON)
    for name in verified_modules:
        relative = Path(*name.split('.')).with_suffix('.olean')
        current = Path('.lake/build/lib/lean')/relative
        before = report/'before-public'/relative
        if side == 'before':
            before.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(current,before)
        else:
            run_logged('compiled-interface-'+name,
                       ['lake','env','lean','--run',str(comparison),str(before),str(current)])

def measure_changed_module(side, sample, module, rows):
    """Fresh single-target rebuild after the corresponding warm two-module unit."""
    clear_outputs([module])
    label = f'{sample}-{side}-module-{module}'
    command = ['lake','--no-cache','--rehash','build','+'+module]
    elapsed = run_logged(label,command)
    log = re.sub(r'\x1b\[[0-9;]*m','',(report/(label+'.log')).read_text())
    assert 'Restored ' not in log, label
    built = set(re.findall(r'\bBuilt\s+([^\s(:]+)',log))
    assert built == {module}, (label,'expected precisely one freshly built target',built)
    artifact = Path('.lake/build/lib/lean',*module.split('.'))
    assert artifact.with_suffix('.olean').is_file()
    artifacts = {key:artifact.with_suffix(suffix).stat().st_size
                 if artifact.with_suffix(suffix).is_file() else None
                 for key,suffix in [('olean','.olean'),('private','.olean.private'),
                                    ('server','.olean.server')]}
    row = {'run':sample,'warmup':sample==0,'side':side,'module':module,
           'command':command,'wall_seconds':elapsed,
           'built_modules':sorted(built),'artifacts':artifacts}
    rows.append(row)
    (report/'module-measurements.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(row),flush=True)

def main():
    base, head = os.environ['BASE'], os.environ['HEAD']
    assert base == '4f5b851cae6872352482cec54ae6f85ff9bae2c5', base
    assert head == 'c76ccd9231db91a362173d33dcd68caf1230fa9a', head
    assert os.environ['MATHLIB'] == 'fc4f59e577feb1a4956671bc04ac18aaaf8cd842'
    assert os.environ['LEAN_COMMIT'] == '611c117bfaf7b7ae1cfcf246ce6fba31e8f509e9'
    assert Path('lean-toolchain').read_text().strip() == 'leanprover/lean4:v4.36.0'
    assert git('rev-parse','HEAD').decode().strip() == head
    assert git('rev-parse','HEAD^').decode().strip() == base
    assert not git('status','--porcelain','--untracked-files=no')
    expected = {str(p):'M' for m,p in zip(mods,paths) if m in changed}
    changes = {line.split('\t')[1]:line.split('\t')[0]
               for line in git('diff','--no-renames','--name-status',base,head).decode().splitlines()}
    assert changes == expected,(changes,expected)
    patch = git('diff','--no-ext-diff',base,head).decode()
    added = '\n'.join(line[1:] for line in patch.splitlines()
                      if line.startswith('+') and not line.startswith('+++'))
    assert not re.search(r'\b(sorry|admit|axiom|unsafe|native_decide)\b', added)
    assert not re.search(r'\b(maxHeartbeats|maxRecDepth|ofReduceBool|ofReduceNat)\b', added)
    subprocess.run(['git','diff','--check',base,head],check=True)
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
    identity = {'scope':'two changed modules','verified_modules':verified_modules,'base':base,'head':head,'mathlib':os.environ['MATHLIB'],'lean':version,
                'lake':subprocess.check_output(['lake','--version'],text=True).strip(),
                'protected_sha256':protected,'package_heads':package_heads,
                'logical_cpu_count':os.cpu_count(),
                'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                'thread_configuration':'LEAN_NUM_THREADS=1 environment; unmodified project/compiler options',
                'explicit_compiler_thread_limit':None,
                'full_Main_Challenge_build':'NOT RUN','comparator':'NOT RUN'}
    (report/'identity.json').write_text(json.dumps(identity,indent=2))
    (report/'source.patch').write_bytes(git('diff','--no-ext-diff',base,head))
    sources = {'before':{m:git('show',f'{base}:{p}') for m,p in zip(mods,paths)},
               'after':{m:git('show',f'{head}:{p}') for m,p in zip(mods,paths) if m in verified_modules}}
    for side,contents in sources.items():
        for m,source in contents.items():
            target = report/'sources'/side/Path(*m.split('.')).with_suffix('.lean')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source)
    rows,module_rows,counts,needed = [],[],{},set()
    try:
        for side in ['before','after']:
            set_sources(sources[side])
            counts[side] = source_counts(sources[side])
            needed.update(deps())
        (report/'imports.json').write_text(json.dumps(counts,indent=2))
        (report/'project-ancestors.json').write_text(json.dumps(sorted(needed),indent=2))
        clear_outputs()
        cache_receipt = restore_deps(needed)
        command = ['lake','--no-cache','--rehash','build',*['+'+m for m in verified_modules]]
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
                for module in changed:
                    measure_changed_module(side,i,module,module_rows)
            if i == 0:
                fresh = set().union(*(set(row['built_modules']) for row in rows if row['warmup']))
                rejected = set(cache_receipt['rejected_cache_modules'])
                assert rejected <= fresh, ('rejected ancestors were not freshly built during warm-up',rejected-fresh)
                cache_receipt['fresh_ancestors_built_during_warmup'] = sorted(rejected & fresh)
                (report/'dependency-restore.json').write_text(json.dumps(cache_receipt,indent=2))
        assert not git('diff','--name-only')
        assert not git('ls-files','--others','--exclude-standard','--','src')
        run_logged('final-candidate-build',command)
        for m in verified_modules:
            run_logged('leanchecker-'+m,['lake','env','leanchecker','--verbose',m])
        summary = {'imports':counts,'project_dependencies':len(needed),
                   'restored_project_dependencies':cache_receipt['restored_project_dependencies'],
                   'fresh_project_dependencies':cache_receipt['fresh_project_dependencies'],
                   'scope':'Two changed modules only, in both variants. Warm Mathlib dependencies; zero project ancestors.',
                   'full_Main_Challenge_build':'NOT RUN','comparator':'NOT RUN'}
        for side in ['before','after']:
            measured = [r for r in rows if r['side']==side and not r['warmup']]
            assert len(measured) == 3, (side,len(measured))
            times = [r['wall_seconds'] for r in measured]
            summary[side] = {'wall_seconds':times,'median_wall_seconds':statistics.median(times),
                             'artifacts':measured[-1]['artifacts'],'unit_artifacts':measured[-1]['unit_artifacts']}
        summary['changed_module_builds'] = {}
        for module in changed:
            group = {}
            for side in ['before','after']:
                measured = [r for r in module_rows
                            if r['module']==module and r['side']==side and not r['warmup']]
                assert len(measured) == 3, (module,side,len(measured))
                times = [r['wall_seconds'] for r in measured]
                group[side] = {'wall_seconds':times,'median_wall_seconds':statistics.median(times),
                               'artifacts':measured[-1]['artifacts']}
            group['observed_median_reduction_percent'] = round(
                100*(1-group['after']['median_wall_seconds']/group['before']['median_wall_seconds']),2)
            summary['changed_module_builds'][module] = group
        summary['unit_observed_median_reduction_percent'] = round(
            100*(1-summary['after']['median_wall_seconds']/summary['before']['median_wall_seconds']),2)
        (report/'summary.json').write_text(json.dumps(summary,indent=2))
        print('SUMMARY_JSON '+json.dumps(summary,sort_keys=True),flush=True)
        write_summary(summary)
    finally:
        set_sources(sources['after'])

def write_summary(summary):
    counts = summary['imports']
    text = '# Denominator-clearing Lean 4.36 compatibility verification\n\n'
    text += '| Metric | Before | After |\n|---|---:|---:|\n'
    text += f"| Median command seconds | {summary['before']['median_wall_seconds']} | {summary['after']['median_wall_seconds']} |\n"
    for key in ['direct_imports','source_mathlib_closure','changed_direct_imports','changed_source_mathlib_closure']:
        text += f"| {key} | {counts['before'][key]} | {counts['after'][key]} |\n"
    for key in ['olean','private','server']:
        text += f"| Unit {key} bytes | {summary['before']['unit_artifacts'][key]} | {summary['after']['unit_artifacts'][key]} |\n"
    text += '\n| Changed target (separate fresh rebuild) | Before median (s) | After median (s) |\n|---|---:|---:|\n'
    for module,values in summary['changed_module_builds'].items():
        text += f"| {module} | {values['before']['median_wall_seconds']} | {values['after']['median_wall_seconds']} |\n"
    text += ('\nOne warm-up per revision, then three pairs in AB, BA, AB order. Stock Lean with '
             'LEAN_NUM_THREADS=1 environment; unmodified project/compiler options. '
             'Each sample rebuilds the two changed modules as a unit, then rebuilds each target separately '
             'against warm dependencies. The separate timings are not a decomposition of the unit time. '
             'Both public interfaces match exactly, the two denominator lemmas use only allowed '
             'axioms, and both final modules are replayed with stock leanchecker.\n')
    text += '\n**Compatibility diagnostic for the two changed modules only. Direct consumers, full `lake build Main Challenge`, and `lake comparator`: NOT RUN.**\n'
    (report/'summary.md').write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as stream: stream.write(text)

if __name__ == '__main__':
    main()
