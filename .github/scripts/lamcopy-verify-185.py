#!/usr/bin/env python3
"""Bounded fork-only target diagnostic; no Main/Challenge/Comparator claim."""
import argparse,hashlib,importlib.util,json,os,shutil,statistics,subprocess,time,traceback
from pathlib import Path
from types import SimpleNamespace
BASE='9c9f665ed79ce0fa8da61bd803b7a4bf1ad62ed0'
CACHE_REV='2ef232d2992c67d457089833b7ec9e0c262f9370'
HEAD='4902a2ece0f1b8058752b5a4d3b853e675de52f0'
TOOLCHAIN='leanprover/lean4:v4.37.0-rc1'
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
        client=load('verify_client',base/'scripts/ci-cache-get.py')
        approved=client.settings.for_toolchain(TOOLCHAIN)
        identities={}
        for root,sha in [(base,BASE),(candidate,HEAD)]:
            if ci.git(root,'rev-parse','HEAD')!=sha:raise ValueError('wrong checkout SHA')
            subprocess.run(['git','-C',str(root),'diff','--quiet','HEAD','--'],check=True)
            identity=client.current_identity(root)
            if identity['toolchain']!=TOOLCHAIN or identity['manifest_sha256']!=approved.DEPENDENCIES:raise ValueError('source does not match approved 4.37 toolchain and dependencies')
            identities[sha]=identity
        protected_absent=[]
        for name in ['lakefile.toml','lake-manifest.json','lean-toolchain',*PROTECTED]:
            before,after=base/name,candidate/name
            if not before.exists() and not after.exists() and name.startswith('comparator/'):
                protected_absent.append(name)
                continue
            if before.read_bytes()!=after.read_bytes():raise ValueError('changed protected/config input: '+name)
        report['protected_paths_absent_in_both_revisions']=protected_absent
        version=subprocess.check_output(['lean','--version'],text=True).strip()
        if not version.startswith(f'Lean (version {approved.VERSION},')or approved.COMMIT not in version:raise ValueError('wrong stock Lean: '+version)
        tc=Path(subprocess.check_output(['lean','--print-prefix'],text=True).strip())
        if not shutil.which('bwrap'):raise ValueError('Bubblewrap required; no unsandboxed fallback')
        report.update(lean_version=version,manifest_sha256=ci.sha256(base/'lake-manifest.json'),source_identities=identities,protected_files_unchanged=PROTECTED,machine={'uname':list(os.uname()),'cpu_count':os.cpu_count(),'meminfo':Path('/proc/meminfo').read_text()})
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
        save();budget();public=state/'baseline-cache';public.mkdir()
        # Use the source-bound successful #185 receipt, not active 4.36 baseline globals.
        raw=client.fetch(f'ci/revisions/{CACHE_REV}.json',client.MAX_RECEIPT)
        if raw is None:raise ValueError('exact #185 cache receipt is unavailable')
        receipt=client.matching_record(raw,identities[BASE])
        if receipt is None or receipt['candidate_head']!=CACHE_REV:raise ValueError('receipt is not a successful build of the exact #185 source/configuration')
        mapping,rows=client.validated_blobs(receipt,identities[BASE])
        filtered=[row for row in rows if row[0]in selected]
        scoped='"2026-03-17"\n'+''.join(json.dumps([row[1],row[2]])+'\n'for row in filtered)
        (public/'selected-outputs.jsonl').write_text(scoped)
        write(out/'public-receipt.json',receipt)
        report['cache']={'revision':CACHE_REV,'map_sha256':receipt['map_sha256'],'manifest_sha256':receipt['module_manifest_sha256'],'selected_project_modules':len(selected),'available_cached_inputs':len(filtered),'fresh_dependency_proof_check':False};save();budget()
        deps=state/'dependencies';deps.mkdir();(deps/'src').mkdir();(deps/'.lake').mkdir()
        for name in ['lakefile.toml','lake-manifest.json','lean-toolchain']:shutil.copyfile(base/name,deps/name)
        env=prep.clean_env();env.update(ELAN_TOOLCHAIN=TOOLCHAIN,MATHLIB_CACHE_GET_URL='https://cache.mathlib.org/mathlib4',LEAN_NUM_THREADS='1',LEAN_ABORT_ON_PANIC='1')
        report['mathlib_cache']=run(['lake','exe','mathlib/cache','get'],deps,'mathlib-cache.log',env);save()
        if report['mathlib_cache']['exit_code']:raise RuntimeError('official Mathlib cache failed')
        packages=deps/'.lake/packages';ci.validate_packages(base,packages);budget()
        cache_env={**env,'LAKE_CACHE_DIR':str(public),'LAKE_CONFIG':str(deps/'lakefile.toml')}
        report['project_cache']=run(['lake','-q','cache','get',str(public/'selected-outputs.jsonl'),'--repo',client.REPOSITORY],deps,'project-cache.log',cache_env);save()
        if report['project_cache']['exit_code']:raise RuntimeError('scoped stock Lake artifact download failed')
        report['cache']['compressed_bytes']=sum(p.stat().st_size for p in(public/'artifacts').iterdir());save()
        for label,(checkout,targets,cone)in layouts.items():
            budget();work=state/label;work.mkdir();project,cache,result,control=[work/x for x in ['project','cache','result','control']]
            for p in [project,cache/'artifacts',result,control]:p.mkdir(parents=True)
            ci.snapshot(checkout,BASE if label=='before'else HEAD,project);ci.validate_packages(project,packages)
            (project/'.lake/packages').mkdir(parents=True);overrides=ci.package_overrides(project,control)
            cone_set=set(cone);case_rows=[row for row in filtered if row[0]in cone_set]
            for filename in {row[2]for row in case_rows}:shutil.copyfile(public/'artifacts'/filename,cache/'artifacts'/filename)
            warm=client.restore.restore_jobs(project,cache,case_rows)
            for job in warm:
                for path in job['base']:Path(path).mkdir(parents=True,exist_ok=True)
                job['base']=['/work/project/'+str(Path(path).relative_to(project))for path in job['base']]
                job['file']='/work/cache/'+str(Path(job['file']).relative_to(cache))
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
