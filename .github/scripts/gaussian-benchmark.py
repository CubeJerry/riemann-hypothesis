from pathlib import Path
import json,os,re,resource,shutil,subprocess,time
repo=Path.cwd()
base='d27f71347abceb76cd37dc8a5fccbe556ec2be90'
modules=['GroundTheory.GlobalFields.TateThesis.'+x for x in ['Gaussian','GaussianComplex','GaussianComplexFourier','GaussianSchwartz']]
paths={m:Path('src')/(m.replace('.','/')+'.lean') for m in modules}
versions={'patch':{m:p.read_bytes() for m,p in paths.items()},'base':{m:subprocess.check_output(['git','show',base+':'+str(p)]) for m,p in paths.items()}}
roots=set()
for v in versions.values():
 for content in v.values():roots.update(re.findall(rb'^(?:public )?import (Mathlib\.[\w.]+)$',content,re.M))
subprocess.run(['lake','exe','mathlib/cache','get',*[r.decode() for r in sorted(roots)]],check=True)
pin=subprocess.check_output(['git','-C','.lake/packages/mathlib','rev-parse','HEAD'],text=True).strip()
assert pin=='31ce06eaadf4a200c0e1407c5f10953cf606b8f8'
print(subprocess.check_output(['lean','--version'],text=True),flush=True)
print('Mathlib',pin,flush=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
def install(rev):
 for m,p in paths.items():p.write_bytes(versions[rev][m])
def run(m,rev,trial):
 p=paths[m]; mod=Path(m.replace('.','/'))
 art=Path('.lake/build/lib/lean')/mod
 art.with_suffix('.trace').unlink(missing_ok=True)
 t=time.monotonic(); a=resource.getrusage(resource.RUSAGE_CHILDREN)
 proc=subprocess.run(['lake','--no-cache','build','+'+m],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 elapsed=time.monotonic()-t;b=resource.getrusage(resource.RUSAGE_CHILDREN)
 print(proc.stdout,flush=True)
 proc.check_returncode()
 if trial:
  assert re.findall(r'Built (\S+) \(',proc.stdout)==[m]
 if trial==0:
  out=Path('gaussian-exports')/rev;out.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(art.with_suffix('.olean'),out/(mod.name+'.olean'))
 imports=json.loads((Path('.lake/build/ir')/mod.with_suffix('.setup.json')).read_bytes())['importArts']
 data=dict(rev=rev,trial=trial,module=mod.name,elapsed=elapsed,cpu=b.ru_utime+b.ru_stime-a.ru_utime-a.ru_stime,imports=len(re.findall(rb'^(?:public )?import ',p.read_bytes(),re.M)),closure=len(imports),olean=art.with_suffix('.olean').stat().st_size,private=art.with_suffix('.olean.private').stat().st_size)
 print('MEASUREMENT',json.dumps(data),flush=True);return data
rows=[]
for trial in range(0,6):
 for rev in (['patch','base'] if trial%2==0 else ['base','patch']):
  install(rev)
  for m in modules:rows.append(run(m,rev,trial))
  Path('gaussian-results.json').write_text(json.dumps(rows,indent=2))
install('patch')
for m in modules:subprocess.run(['lake','env','leanchecker',m],check=True)

subprocess.run(['lean','--run','.github/scripts/gaussian-exports.lean','gaussian-exports/base','gaussian-exports/patch',*[m.split('.')[-1] for m in modules]],check=True)
