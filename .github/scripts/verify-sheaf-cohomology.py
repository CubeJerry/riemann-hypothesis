from pathlib import Path
import json,os,re,subprocess as sp,time,statistics,resource
base='4d25b0edc80cbf28a7b82a9d491d95875b36e826'
head='fe445c3f8e45458ab3cafce1e7f2a8c9cfd741e5'
queue='e21c8eccfea62e236c7ce233a62e365a8b6de7dc'
paths=[Path(p) for p in sp.check_output(['git','diff','--name-only',base,head],text=True).splitlines()]; assert len(paths)==4
paths.sort(key=lambda p:p.stem.startswith('PushComparison'))
goals=['Development.AbelianVarietyTheory.Proofs.CoherentCohomologyProofs.SumNegOnePowFinrankEqZero','Development.AbelianVarietyTheory.Proofs.CoherentCohomologyProofs.HigherDirectImagesVanishOfIsAffineHom']
def mod(p):return '.'.join(p.relative_to('src').with_suffix('').parts)
def git(*args):return sp.check_output(['git',*args])
def lake(*args):return sp.run(['lake','--no-cache',*args],check=True)
roots=set();seen=set()
def visit(m):
 if m in seen:return
 seen.add(m);s=git('show',base+':src/'+m.replace('.','/')+'.lean').decode()
 for k in re.findall(r'^(?:public |meta )*import ([\w.]+)$',s,re.M):
  if k.startswith('Mathlib.'):roots.add(k)
  elif k.split('.')[0] in ('Development','Formalism','GroundTheory','Lemmata','ReciprocityTheory','CompanionTheory','PositivityTheory','Supplements'):visit(k)
for m in [mod(p) for p in paths]+goals:visit(m)
sp.run(['lake','exe','mathlib/cache','get',*sorted(roots)],check=True)
rows=[]; report=Path(os.environ['GITHUB_STEP_SUMMARY'])
for i,v in enumerate([base,head,head,base]):
 label='before' if v==base else 'after';git('restore','--source='+v,'--worktree','--',*map(str,paths)); print('ROUND',i,label,flush=True)
 for p in paths:
  art=Path('.lake/build/lib/lean')/p.relative_to('src');art.with_suffix('.trace').unlink(missing_ok=True); start=time.monotonic();usage0=resource.getrusage(resource.RUSAGE_CHILDREN);cp=sp.run(['lake','--no-cache','build','+'+mod(p)],stdout=sp.PIPE,stderr=sp.STDOUT,text=True); print(cp.stdout,flush=True);cp.check_returncode();elapsed=time.monotonic()-start;usage1=resource.getrusage(resource.RUSAGE_CHILDREN)
  built=re.findall(r'(?:Built|Rebuilt) (\S+) \(([^()]+)\)',cp.stdout);assert [m for m,t in built if not m.startswith(('Mathlib.','Batteries.'))]==[mod(p)],built
  setup=Path('.lake/build/ir')/p.relative_to('src');imports=json.loads(setup.with_suffix('.setup.json').read_text())['importArts'];row={'round':i,'version':label,'module':p.stem,'direct':len(re.findall(r'^(?:public |meta )*import ',p.read_text(),re.M)),'mathlib':sum(m.startswith('Mathlib.') for m in imports),'olean':art.with_suffix('.olean').stat().st_size,'cpu':round(usage1.ru_utime+usage1.ru_stime-usage0.ru_utime-usage0.ru_stime,3),'wall':round(elapsed,3),'lake':built[-1][1]};rows.append(row);print('MEASURE',json.dumps(row),flush=True)
with report.open('a') as f:
 print('| Module | Direct imports | Mathlib closure | Public `.olean` bytes | Rebuild wall (s), median of two |\n|---|---:|---:|---:|---:|',file=f)
 for p in paths:
  a,b=([r for r in rows if r['module']==p.stem and r['version']==v] for v in ('before','after'));pairs=[str(a[0][k])+' → '+str(b[0][k]) for k in ('direct','mathlib','olean')]+[f"{statistics.median(r['wall'] for r in a):.2f} → {statistics.median(r['wall'] for r in b):.2f}"];print('| '+p.stem+' | '+' | '.join(pairs)+' |',file=f)
git('restore','--source='+head,'--worktree','--',*map(str,paths));lake('build',*['+'+g for g in goals]);
for p in paths:lake('env','leanchecker','--verbose',mod(p))
saved=git('diff','--binary',base,head);git('fetch','--depth=1','https://github.com/leanprover-community/riemann-hypothesis.git',queue);git('checkout','--detach',queue);sp.run(['git','apply','--check','-'],input=saved,check=True);sp.run(['git','apply','-'],input=saved,check=True);
for p in paths:
 art=Path('.lake/build/lib/lean')/p.relative_to('src');art.with_suffix('.trace').unlink(missing_ok=True);lake('build','+'+mod(p))
with report.open('a') as f:print('\nAll four targets rebuilt on #438 at `'+queue[:12]+'`. Both downstream targets and all four `leanchecker` checks passed on the PR head.',file=f)
