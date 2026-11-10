// Re-read only the exact successful published original package provisioning on a standard hosted runner.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,run_id=42868076233,source='a1c48b762333c084e8c8321668c5fd87a94cc0f6';
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact existing public repository required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 if(run.head_sha!==source||run.head_branch!=='qualification/class-package-official-pool-preflight-v2'||run.path!=='.github/workflows/phase6-original-package-official-pool-preflight-retry.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||jobs.length!==1||jobs[0].id!==130011660555||jobs[0].head_sha!==source||jobs[0].status!=='completed'||jobs[0].conclusion!=='success'||JSON.stringify(jobs[0].labels)!==JSON.stringify(['ubuntu-24.04']))throw Error('Exact completed original package preflight and standard Ubuntu job required');
 const base='out/original-pool-published-inputs',artifacts={};fs.mkdirSync(base,{recursive:true});
 for(const [kind,id,size,digest,name] of [
  ['raw',13789795378,63441040,'a83693ddec0408090682e14c4c8a9e0b89b4232d7d8b604a1e35abc442b587ae','original-package-official-pool-full-provisioning-evidence'],
  ['small',13789930127,98817,'d10e09042bbb2aadc8d6933d80d15dce426213bb650d80d4dfc4504756652a94','original-package-official-pool-small-preflight-receipt']]){
  const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:id})).data;artifacts[kind]=artifact;
  fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifacts},null,2));
  if(artifact.id!==id||artifact.name!==name||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.expired||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==source||artifact.workflow_run.head_branch!==run.head_branch)throw Error('Exact source-bound original published '+kind+' provisioning artifact required');
  const transport=base+'/'+kind;fs.mkdirSync(transport,{recursive:true});
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base:transport,core})).data);
  if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual original published '+kind+' provisioning ZIP differs');
  fs.writeFileSync(base+'/'+kind+'.zip',bytes,{flag:'wx'});
 }
};
