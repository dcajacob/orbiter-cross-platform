// Retain the exact complete original SDK inventory; this metadata grants no capability qualification.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact public repository required');
 const run_id=42754222747,head='493ef1508ba2a09effec8a8bc30afb9f61d3aa0c',artifact_id=13734667876;
 const size=68946,digest='103eb95d3b2da79fe0366dea26bfdf6b55d419cac3287ab3a6acad9cfbae5c24';
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
 const base='out/class-capability-inventory';fs.mkdirSync(base,{recursive:true});
 fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==run_id||run.head_sha!==head||run.head_branch!=='qualification/native-class-capability-reference-v3'||run.path!=='.github/workflows/phase6-class-capability-reference.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    jobs.length!==1||jobs[0].id!==129624723384||jobs[0].run_id!==run_id||jobs[0].head_sha!==head||jobs[0].status!=='completed'||jobs[0].conclusion!=='success'||JSON.stringify(jobs[0].labels)!==JSON.stringify(['ubuntu-24.04'])||
    artifact.id!==artifact_id||artifact.name!=='original-full-SDK-capability-inventory'||artifact.expired||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact complete source-bound SDK inventory required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual published SDK inventory differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 core.info('Complete original SDK inventory retained with all full seventeen-field variants; no runtime or broader qualification credit');
};
