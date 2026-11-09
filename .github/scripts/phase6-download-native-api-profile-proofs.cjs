// Retain only the complete actual independent native API profile proof artifacts.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform')throw Error('Exact authorized repository required');
 const run_id=context.runId,run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id,per_page:100});
 if(run.head_sha!==context.sha||run.run_attempt!==1||run.head_branch!=='qualification/native-general-api-independent-v1'||run.path!=='.github/workflows/phase6-native-general-api-independent.yml')throw Error('Exact actual independent source run required');
 for(const c of ['Debug','Release'])for(const m of ['automatic','sse2']){
  const profile=c+'-'+m,found=artifacts.filter(a=>a.name==='independent-native-GeneralApi-'+profile&&!a.expired),selected=jobs.filter(j=>j.name==='Independently audit native API '+profile);
  if(found.length!==1||selected.length!==1||selected[0].head_sha!==context.sha||selected[0].status!=='completed'||selected[0].conclusion!=='success'||!selected[0].labels.includes('ubuntu-24.04')||selected[0].labels.includes('self-hosted'))throw Error('Complete actual independent native API profile required');
  const artifact=found[0],base='out/native-api-profile-proofs/'+profile;fs.mkdirSync(base,{recursive:true});
  fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
  if(artifact.size_in_bytes>=16*1024**2)throw Error('Independent proof must be bounded metadata only');
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
  if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)throw Error('Independent native API proof ZIP digest/size differs');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
};
