// Consume only this source's actually completed qualification job; never synthesize status.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,run_id=context.runId;
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id,per_page:100});
 const found=artifacts.filter(a=>a.name==='joint-GeneralApi-qualified-reference'&&!a.expired),selected=jobs.filter(j=>j.name==='Joint original API qualification');
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||run.head_sha!==context.sha||run.head_branch!=='qualification/joint-general-api-v1'||run.path!=='.github/workflows/phase6-joint-general-api.yml'||run.run_attempt!==1||
    jobs.length!==2||selected.length!==1||selected[0].status!=='completed'||selected[0].conclusion!=='success'||found.length!==1||
    jobs.some(j=>j.run_id!==run_id||j.head_sha!==context.sha||JSON.stringify(j.labels)!==JSON.stringify(['ubuntu-24.04'])))throw Error('Exact actual passed joint qualification and standard-runner replay roster required');
 const artifact=found[0],base='out/joint-api-published';fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==context.sha||artifact.size_in_bytes>=32*1024**2)throw Error('Bounded same-source published qualification proof required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)throw Error('Actual published qualification ZIP digest/length differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
