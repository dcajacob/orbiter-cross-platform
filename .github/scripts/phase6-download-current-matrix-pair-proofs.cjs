// Bind all four actual direct-build proof artifacts to this exact hosted workflow source/run.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,run_id=Number(process.env.GITHUB_RUN_ID);
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact existing public repository required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 if(run.head_sha!==context.sha||run.run_attempt!==1||run.head_branch!=='codex/current-native-matrix-v1'||run.path!=='.github/workflows/phase6-current-native-matrix.yml') throw Error('Exact actual same-source direct-build producer required');
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id,per_page:100}),ids=new Set();
 for(const mode of ['automatic','sse2']) for(const phase of ['stock','reload']){
  const name='Direct current native builds '+mode+' '+phase,matching=jobs.filter(j=>j.name===name);
  if(matching.length!==1||matching[0].head_sha!==context.sha||matching[0].status!=='completed'||matching[0].conclusion!=='success'||!matching[0].labels.includes('ubuntu-24.04')||matching[0].labels.includes('self-hosted')) throw Error('Every actual direct-build phase must complete successfully');
  const selected=artifacts.filter(a=>a.name==='current-native-direct-build-'+mode+'-'+phase);
  if(selected.length!==1) throw Error('Unique completed direct-build artifact required');const artifact=selected[0];
  if(ids.has(artifact.id)||artifact.expired||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==context.sha||artifact.size_in_bytes<=0||artifact.size_in_bytes>=4*1024**3||!/^sha256:[0-9a-f]{64}$/.test(artifact.digest)) throw Error('Exact direct-build API source/identity required');ids.add(artifact.id);
  const base='out/current-matrix-pair-inputs/'+mode+'-'+phase;fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
  const bytes=Buffer.from((await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'})).data);
  if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest) throw Error('Actual direct-build raw proof bytes differ');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
 core.info('Independently retained all four actual same-source direct-build proof ZIPs; overall final job still needs to audit them');
};
