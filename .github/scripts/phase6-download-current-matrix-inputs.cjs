// Exact complete existing capture/proof archives; all bulk bytes remain on public hosted runners.
module.exports=async ({github,context,core,metadataOnly=false,proofsOnly=false})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact existing public repository required');
 const plan=JSON.parse(fs.readFileSync('out/native-matrix-plan.json','utf8'));
 if(plan.current_physical_source!=='dbf5a3c1d78a691af9714ce3b5e4d4312045759f'||plan.current_physical_run_id!==42675771025||
    plan.current_capture_source!=='eaf9b0a802af9f8a1b57a0721818224340ac22af'||plan.current_capture_run!==42590249236) throw Error('Exact actual current physical and capture sources required');
 await require('./phase6-download-native-matrix-inputs.cjs')({github,context,core,metadataOnly,proofsOnly});
 async function record(run_id){return {run:(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs:await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100})};}
 async function retain(base,source,artifact,binary=true){
  if(artifact.expired||artifact.workflow_run.id!==source.run.id||artifact.workflow_run.head_sha!==source.run.head_sha||!/^sha256:[0-9a-f]{64}$/.test(artifact.digest)||
     artifact.size_in_bytes<=0||artifact.size_in_bytes>=4*1024**3) throw Error('Exact unexpired source/API archive required');
  fs.mkdirSync(base,{recursive:true});const api={repository:context.repo,...source,artifact};
  fs.writeFileSync(base+'/api.json',JSON.stringify(api,null,2),{flag:'wx'});
  if(binary){const bytes=Buffer.from((await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'})).data);
   if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest) throw Error('Actual raw API length/digest differs');
   fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});}
  return api;
 }
 const physical=await record(plan.current_physical_run_id),run=physical.run;
 if(run.head_sha!==plan.current_physical_source||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    run.head_branch!=='qualification/current-shader-physical-audit-v1'||run.path!=='.github/workflows/phase6-current-shader-physical-audit.yml'||
    physical.jobs.length!==9||physical.jobs.some(j=>j.run_id!==run.id||j.head_sha!==run.head_sha||j.run_attempt!==1||j.status!=='completed'||j.conclusion!=='success'||
      !j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))) throw Error('All eight exact successful current physical phases required');
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:run.id,per_page:100}),readiness=[],ids=new Set();
 const names=plan.current_cells.map(c=>'shader-current-original-physical-'+c.join('-')).concat(['current-original-physical-readiness']);
 if(artifacts.length!==9||new Set(artifacts.map(a=>a.name)).size!==9||artifacts.some(a=>!names.includes(a.name))) throw Error('Exact eight phase reports plus preserved readiness archive required');
 for(const cell of plan.current_cells){
  const selected=artifacts.filter(a=>a.name==='shader-current-original-physical-'+cell.join('-'));
  if(selected.length!==1||ids.has(selected[0].id)) throw Error('Unique actual current physical phase required');ids.add(selected[0].id);
  readiness.push({cell,api:await retain('out/current-matrix-phase-inputs/'+cell.join('-'),physical,selected[0],!metadataOnly)});
 }
 fs.writeFileSync('out/current-matrix-readiness.json',JSON.stringify(readiness,null,2),{flag:'wx'});
 if(metadataOnly||proofsOnly)return;
 const current=await record(plan.current_capture_run),mode=process.env.MATH_PROFILE,phase=process.env.CURRENT_PHASE;
 if(current.run.head_sha!==plan.current_capture_source||current.run.run_attempt!==1||current.run.status!=='completed'||current.run.conclusion!=='success'||
    current.run.head_branch!=='qualification/current-stock-capture-v4'||current.run.path!=='.github/workflows/phase6-current-shader-stock.yml'||
    current.jobs.length!==9||current.jobs.some(j=>j.run_id!==current.run.id||j.head_sha!==current.run.head_sha||j.status!=='completed'||j.conclusion!=='success'||
      !j.labels.includes(j.name==='readiness'?'ubuntu-24.04':'windows-2025')||j.labels.includes('self-hosted'))||
    !['automatic','sse2'].includes(mode)||!['stock','reload'].includes(phase)) throw Error('Exact complete source current capture cohort and pair required');
 const captures=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:current.run.id,per_page:100});
 for(const configuration of ['Debug','Release']){
  const cell=[configuration,mode,phase],selected=captures.filter(a=>a.name==='shader-source-complete-current-stock-'+cell.join('-'));
  if(selected.length!==1) throw Error('Unique actual current raw capture artifact required');
  await retain('out/current-matrix-current-inputs/'+cell.join('-'),current,selected[0]);
 }
 core.info('All current/native raw bytes and sixteen physical proof archives verified on GitHub only; no capture reruns or qualification inferred');
};
