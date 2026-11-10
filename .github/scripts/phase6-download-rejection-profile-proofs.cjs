// Read only completed immutable profile audits and the completed original four-profile capture.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/Closeout/class-rejection-profile-proofs-v1.lock.json','utf8'));
 const raw=JSON.parse(fs.readFileSync('Tests/Production/Closeout/class-rejection-published-inputs-v1.lock.json','utf8'));
 const profiles=['Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'];
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private||JSON.stringify(Object.keys(lock.profiles).sort())!==JSON.stringify([...profiles].sort())||JSON.stringify(Object.keys(raw.profiles).sort())!==JSON.stringify([...profiles].sort()))throw Error('All four exact public original rejection profiles required');
 const root='out/rejection-profile-proofs';fs.mkdirSync(root,{recursive:true});
 const get=async pin=>{
  const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:pin.run_id})).data;
  const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:pin.run_id,per_page:100});
  if(run.id!==pin.run_id||run.head_sha!==pin.source||run.head_branch!==pin.branch||run.path!==pin.workflow||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||jobs.length!==5||Object.keys(pin.jobs).length!==5||new Set(jobs.map(j=>j.id)).size!==5||jobs.some(j=>pin.jobs[j.id]!==j.name||j.run_id!==run.id||j.head_sha!==run.head_sha||j.status!=='completed'||j.conclusion!=='success'||JSON.stringify(j.labels)!==JSON.stringify(['ubuntu-24.04'])))throw Error('Complete exact five-job standard-runner source required');
  return {repository:context.repo,run,jobs};
 };
 const capture=await get(raw);fs.writeFileSync(root+'/capture-final-api.json',JSON.stringify(capture,null,2),{flag:'wx'});
 for(const profile of profiles){
  const pin=lock.profiles[profile],source=await get(pin),artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.artifact_id})).data;
  if(artifact.id!==pin.artifact_id||artifact.expired||artifact.name!=='independent-original-rejections-full-witness-'+profile||artifact.size_in_bytes!==pin.archive_bytes||artifact.digest!=='sha256:'+pin.archive_sha256||artifact.workflow_run.id!==pin.run_id||artifact.workflow_run.head_sha!==pin.source)throw Error('Exact complete independently published profile witness required');
  const base=root+'/'+profile;fs.mkdirSync(base);fs.writeFileSync(base+'/api.json',JSON.stringify({...source,artifact},null,2),{flag:'wx'});
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source,artifact,base,core})).data);
  if(bytes.length!==pin.archive_bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==pin.archive_sha256)throw Error('Published profile witness actual bytes differ');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
};
