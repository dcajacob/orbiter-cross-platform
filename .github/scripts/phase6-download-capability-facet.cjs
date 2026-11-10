// Read only six small, independently verified published receipts on a standard hosted runner.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/Closeout/capability-facet-published-inputs-v1.lock.json','utf8'));
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private||
    JSON.stringify(Object.keys(lock.observers).sort())!==JSON.stringify(['Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'])||
    JSON.stringify(Object.keys(lock.sdk).sort())!==JSON.stringify(['automatic','sse2']))throw Error('Exact six public complete capability receipts required');
 for(const group of ['observers','sdk'])for(const [key,pin] of Object.entries(lock[group])){
  const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:pin.run_id})).data;
  const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:pin.run_id,per_page:100});
  const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.artifact_id})).data;
  const base='out/capability-facet-inputs/'+group+'/'+key;fs.mkdirSync(base,{recursive:true});
  fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
  if(run.id!==pin.run_id||run.head_sha!==pin.source||run.head_branch!==pin.branch||run.path!==pin.workflow||
     run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||jobs.length!==Object.keys(pin.jobs).length||
     new Set(jobs.map(j=>j.id)).size!==jobs.length||jobs.some(j=>pin.jobs[j.id]!==j.name||j.run_id!==run.id||j.head_sha!==pin.source||
       j.status!=='completed'||j.conclusion!=='success'||JSON.stringify(j.labels)!==JSON.stringify(['ubuntu-24.04']))||
     artifact.id!==pin.artifact_id||artifact.name!==pin.artifact_name||artifact.expired||artifact.size_in_bytes!==pin.archive_bytes||
     artifact.digest!=='sha256:'+pin.archive_sha256||artifact.workflow_run.id!==pin.run_id||artifact.workflow_run.head_sha!==pin.source)
       throw Error('Exact complete capability receipt/API/source required: '+group+'/'+key);
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
  if(bytes.length!==pin.archive_bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==pin.archive_sha256)throw Error('Actual capability receipt ZIP differs');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
 core.info('Retained only six exact independent capability observer/SDK metadata receipts; no simulator launched');
};
