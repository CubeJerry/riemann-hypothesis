#!/usr/bin/env python3
"""Bounded fork-only target diagnostic; no Main/Challenge/Comparator claim."""
import argparse,hashlib,importlib.util,json,os,shutil,statistics,subprocess,time,traceback
from pathlib import Path
from types import SimpleNamespace
BASE='c592e91eb8f41bfd149227c09460fae0c17bf3c5'
HEAD='acb08b84d95e0f40647acb5bfdfab6696365cbf0'
PREFIX='Development.AbelianVarietyTheory.Proofs.IwasawaDecomposition.'
TARGETS=[PREFIX+x for x in ['CopyAll','RingSpecNormalisedCharacterEq','LamCopy','ExportTieMove']]
PROTECTED=['src/Challenge.lean','src/Statements.lean','comparator.json','export-targets.txt','comparator/FormalConjecturesChallenge.lean','comparator/formal-conjectures.json','comparator/formal-conjectures-export-targets.txt']
START=time.monotonic()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(args):
    base,candidate,out,state=[Path(x).resolve()for x in [args.base,args.candidate,args.output,args.state]]
    out.mkdir(parents=True,exist_ok=True);state.mkdir(parents=True,exist_ok=True)
    report={'status':'started','full_build':False,'comparator_run':False,'base_sha':BASE,'candidate_sha':HEAD,'cases':{}}
    def save():write(out/'result.json',report)
    try:
        ci=load('verify_ci',base/'scripts/ci-build.py');prep=load('verify_prep',base/'scripts/ci-prepare.py');quick=load('verify_quick',base/'scripts/quick-check.py')
        for root,sha in [(base,BASE),(candidate,HEAD)]:
            if ci.git(root,'rev-parse','HEAD')!=sha:raise ValueError('wrong checkout SHA')
            subprocess.run(['git','-C',str(root),'diff','--quiet','HEAD','--'],check=True);ci.validate_inputs(root,ci.DEPENDENCIES)
        for name in ['lakefile.toml','lake-manifest.json','lean-toolchain',*PROTECTED]:
            if(base/name).read_bytes()!=(candidate/name).read_bytes():raise ValueError('changed protected/config input: '+name)
        version=subprocess.check_output(['lean','--version'],text=True).strip()
        if not version.startswith(f'Lean (version {ci.settings.VERSION},')or ci.settings.COMMIT not in version:raise ValueError('wrong stock Lean: '+version)
        tc=Path(subprocess.check_output(['lean','--print-prefix'],text=True).strip())
        if not shutil.which('bwrap'):raise ValueError('Bubblewrap required; no unsandboxed fallback')
        report.update(lean_version=version,manifest_sha256=ci.sha256(base/'lake-manifest.json'),protected_files_unchanged=PROTECTED,machine={'uname':list(os.uname()),'cpu_count':os.cpu_count(),'meminfo':Path('/proc/meminfo').read_text()})
        def budget():
            if shutil.disk_usage(state).free<3*1024**3:raise RuntimeError('less than 3 GiB free; diagnostic stopped')
            if time.monotonic()-START>80*60:raise RuntimeError('80-minute diagnostic budget exhausted')
        def run(command,root,filename,env,limit=1800):
            budget();print('RUN',filename,flush=True);start=time.monotonic()
            previous=Path.cwd()
            try:
                os.chdir(root)
                with(out/filename).open('wb')as log:code=ci.supervised_build(command,env,log,[root],3,timeout_seconds=min(limit,max(1,int(80*60-(time.monotonic()-START)))))
            finally:os.chdir(previous)
            item={'command':command,'exit_code':code,'wall_seconds':time.monotonic()-start,'log':filename};print(json.dumps(item),flush=True)
            if code:print((out/filename).read_text(errors='replace')[-16000:],flush=True)
            return item
        layouts={};selected=set()
        for label,root in [('before',base),('after',candidate)]:
            targets=[m for m in TARGETS if(root/'src'/(m.replace('.','/')+'.lean')).is_file()]
            cone=quick.dependency_closure(root,targets,maximum=20000);layouts[label]=(root,targets,cone);selected.update(cone)
            report['cases'][label]={'targets':targets,'project_closure_count':len(cone),'builds':[],'modules':{}}
            (out/(label+'-closure.txt')).write_text('\n'.join(cone)+'\n')
        save();budget();prep.settings.require_baseline();public=state/'baseline-cache';public.mkdir()
        mapping=prep.get(f'{prep.BASE}/revisions/{prep.REPO}/tc/{prep.settings.TOOLCHAIN_DIR}/{prep.REVISION}.jsonl');manifest=prep.get(f'{prep.BASE}/bootstrap/{prep.REVISION}/modules.jsonl.gz')
        if prep.digest(mapping)!=prep.MAP_SHA or prep.digest(manifest)!=prep.MANIFEST_SHA:raise ValueError('baseline metadata hash mismatch')
        (public/'outputs.jsonl').write_bytes(mapping);(public/'modules.jsonl.gz').write_bytes(manifest)
        entries=prep.mapping(mapping);hashes=prep.manifest_hashes(manifest,entries,mapping);scoped=prep.select_module_entries(manifest,entries,selected)
        report['cache']={'revision':prep.REVISION,'map_sha256':prep.MAP_SHA,'manifest_sha256':prep.MANIFEST_SHA,'selected_project_modules':len(selected),'available_cached_inputs':len(scoped),'fresh_dependency_proof_check':False};save();budget()
        deps=state/'dependencies';deps.mkdir();(deps/'src').mkdir();(deps/'.lake').mkdir()
        for name in ['lakefile.toml','lake-manifest.json','lean-toolchain']:shutil.copyfile(base/name,deps/name)
        env=prep.clean_env();env.update(ELAN_TOOLCHAIN=prep.TOOLCHAIN,MATHLIB_CACHE_GET_URL='https://cache.mathlib.org/mathlib4',LEAN_NUM_THREADS='1',LEAN_ABORT_ON_PANIC='1')
        report['mathlib_cache']=run(['lake','exe','mathlib/cache','get'],deps,'mathlib-cache.log',env);save()
        if report['mathlib_cache']['exit_code']:raise RuntimeError('official Mathlib cache failed')
        packages=deps/'.lake/packages';ci.validate_packages(base,packages);budget();pairs=list(scoped.items())
        for index in range(0,len(pairs),100):
            budget();prep.downloads(public,dict(pairs[index:index+100]),hashes);print(f'Cached {min(index+100,len(pairs))}/{len(pairs)}',flush=True)
        report['cache']['compressed_bytes']=sum(p.stat().st_size for p in(public/'artifacts').iterdir());save()
        for label,(checkout,targets,cone)in layouts.items():
            budget();work=state/label;work.mkdir();project,cache,result,control=[work/x for x in ['project','cache','result','control']]
            for p in [project,cache/'artifacts',result,control]:p.mkdir(parents=True)
            ci.snapshot(checkout,BASE if label=='before'else HEAD,project);ci.validate_inputs(project,ci.DEPENDENCIES);ci.validate_packages(project,packages)
            (project/'.lake/packages').mkdir(parents=True);overrides=ci.package_overrides(project,control)
            opts=SimpleNamespace(baseline_manifest=public/'modules.jsonl.gz',baseline_manifest_sha256=prep.MANIFEST_SHA,baseline_map=public/'outputs.jsonl',baseline_cache=public)
            _,warm,_=ci.baseline(opts,project,cache,modules=set(cone))
            # Lake --rehash writes hash sidecars; use private dependency copies.
            private=ci.private_package_builds(project,packages,work/'dependency-builds')
            budget()
            sandbox=ci.sandbox(tc,project,packages,cache,result,control,1,private)
            sandbox=sandbox[:-2]+['--setenv','LEAN_ABORT_ON_PANIC','1']+sandbox[-2:]
            if warm:subprocess.run(sandbox+['/opt/lean/bin/leantar','--jobs','1','-f','-x','-j','-'],input=json.dumps(warm),text=True,env=ci.trusted_env(),check=True,timeout=900)
            command=sandbox+['/opt/lean/bin/lake','--packages',overrides,'--rehash','build']
            item=run(command+['+'+m for m in targets],project,label+'-warm.log',ci.trusted_env());report['cases'][label]['warm_build']=item;save()
            if item['exit_code']:raise RuntimeError(label+' warm build failed')
            fresh=sandbox+['env','LAKE_ARTIFACT_CACHE=false','LAKE_RESTORE_ARTIFACTS=false','/opt/lean/bin/lake','--packages',overrides,'--rehash','build']
            for target in targets:
                times=[]
                for repeat in range(3 if target.endswith('.LamCopy')else 1):
                    for folder in ['lib/lean','ir']:
                        stem=project/'.lake/build'/folder/target.replace('.','/')
                        for p in stem.parent.glob(stem.name+'.*'):
                            if p.is_file()or p.is_symlink():p.unlink()
                    name=f'{label}-{target.rsplit(".",1)[-1]}-{repeat+1}.log';item=run(fresh+['+'+target],project,name,ci.trusted_env(),900);item.update(target=target,repetition=repeat+1)
                    report['cases'][label]['builds'].append(item);save()
                    if item['exit_code']:raise RuntimeError(label+' target failed: '+target)
                    times.append(item['wall_seconds'])
                source=project/'src'/(target.replace('.','/')+'.lean');olean=project/'.lake/build/lib/lean'/(target.replace('.','/')+'.olean')
                report['cases'][label]['modules'][target]={'direct_import_count':len(quick.imports(source)),'project_ancestor_count':len(quick.dependency_closure(project,[target],maximum=20000))-1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'olean_bytes':olean.stat().st_size,'build_seconds':times,'median_seconds':statistics.median(times)};save()
            ci.verify_private_packages(project,packages,private);ci.validate_packages(project,packages);report['cases'][label]['status']='touched_targets_and_consumer_pass';save();shutil.rmtree(work)
        report['status']='scoped_verification_pass'
    except BaseException as error:
        report.update(status='failed_or_resource_limited',error=f'{type(error).__name__}: {error}');(out/'exception.txt').write_text(traceback.format_exc());raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-START,free_bytes_at_end=shutil.disk_usage(state).free);save();print(json.dumps({k:report.get(k)for k in ['status','error','elapsed_seconds','full_build','comparator_run']}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['base','candidate','output','state']:p.add_argument('--'+key,required=True)
    main(p.parse_args())
