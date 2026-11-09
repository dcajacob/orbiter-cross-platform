// Download exact existing source-bound inputs on GitHub only; retain original APIs and failures.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/GeneralApiCorrection/Hosted/joint-api-inputs-v1.lock.json','utf8'));
 if(owner!==lock.repository.owner||repo!==lock.repository.repo||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact already-public qualification repository required');
 const cache=new Map();
 for(const [name,pin] of Object.entries(lock.inputs)){
  if(!cache.has(pin.run_id)){
   const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:pin.run_id})).data;
   const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:pin.run_id,per_page:100});
   cache.set(pin.run_id,{run,jobs});
  }
  const {run,jobs}=cache.get(pin.run_id),artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.artifact_id})).data;
  const base='out/joint-api-inputs/'+name;fs.mkdirSync(base,{recursive:true});
  fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
  if(run.id!==pin.run_id||run.head_sha!==pin.source||run.head_branch!==pin.branch||run.path!==pin.workflow||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
     artifact.id!==pin.artifact_id||artifact.name!==pin.artifact_name||artifact.expired||artifact.size_in_bytes!==pin.archive_bytes||artifact.digest!=='sha256:'+pin.archive_sha256||
     artifact.workflow_run.id!==pin.run_id||artifact.workflow_run.head_sha!==pin.source||jobs.length!==Object.keys(pin.jobs).length||new Set(jobs.map(j=>j.id)).size!==jobs.length)throw Error('Exact actual joint input run/artifact/roster differs: '+name);
  for(const j of jobs){
   const expected=pin.jobs[j.id];
   if(!expected||j.run_id!==pin.run_id||j.head_sha!==pin.source||j.name!==expected.name||j.status!==expected.status||j.conclusion!==expected.conclusion||
      JSON.stringify(j.labels)!==JSON.stringify(expected.labels)||j.labels.some(l=>!['ubuntu-24.04','windows-2025'].includes(l)))throw Error('Exact actually completed standard-runner input job differs: '+name);
  }
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
  if(bytes.length!==pin.archive_bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==pin.archive_sha256)throw Error('Actual immutable joint input ZIP differs: '+name);
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
  core.info('Retained exact existing source-bound joint input '+name+'; no simulator or local transfer');
 }
};
