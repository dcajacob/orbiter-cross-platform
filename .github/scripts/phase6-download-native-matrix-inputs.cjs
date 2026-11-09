// Exact existing public hosted inputs only. Every binary download is API size/SHA bound.
module.exports=async ({github,context,core,metadataOnly=false,proofsOnly=false})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact existing public repository required');
 const plan=JSON.parse(fs.readFileSync('out/native-matrix-plan.json','utf8'));
 if(plan.physical_source!=='6ca9af318e625e263deed144e62525e3632fb9ee'||plan.physical_run_id!==42625357330) throw Error('Exact immutable physical cohort required');
 async function record(run_id){return {run:(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs:await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100})};}
 async function retain(base,source,artifact,binary=true){
  if(artifact.expired||artifact.workflow_run.id!==source.run.id||artifact.workflow_run.head_sha!==source.run.head_sha||!/^sha256:[0-9a-f]{64}$/.test(artifact.digest)||artifact.size_in_bytes<=0||artifact.size_in_bytes>=4*1024**3) throw Error('Exact unexpired canonical API artifact required');
  fs.mkdirSync(base,{recursive:true});const api={repository:context.repo,...source,artifact};fs.writeFileSync(base+'/api.json',JSON.stringify(api,null,2),{flag:'wx'});
  if(binary){const bytes=Buffer.from((await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'})).data);
   if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest) throw Error('Actual API ZIP length/digest differs: '+artifact.id);
   fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});}
  return api;
 }
 const physical=await record(plan.physical_run_id),run=physical.run;
 if(run.head_sha!==plan.physical_source||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||run.head_branch!=='qualification/native-original-physical-audit-v1'||run.path!=='.github/workflows/phase6-native-original-physical-audit.yml'||
    physical.jobs.length!==9||physical.jobs.some(j=>j.run_id!==run.id||j.head_sha!==run.head_sha||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))) throw Error('All eight actual physical phases must finish successfully before matrix work');
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:run.id,per_page:100}),readiness=[];const ids=new Set();
 for(const profile of plan.profiles) for(const phase of plan.phases){
  const name='native-original-physical-'+profile+'-'+phase,selected=artifacts.filter(a=>a.name===name);
  if(selected.length!==1||ids.has(selected[0].id)) throw Error('Unique actual closed phase artifact required: '+name);ids.add(selected[0].id);
  readiness.push({profile,phase,api:await retain('out/native-matrix-phase-inputs/'+profile+'-'+phase,physical,selected[0],!metadataOnly)});
 }
 fs.writeFileSync('out/native-matrix-readiness.json',JSON.stringify(readiness,null,2),{flag:'wx'});
 if(metadataOnly||proofsOnly){core.info('Preserved every exact physical phase API identity'+(metadataOnly?'':' and verified all eight actual raw report ZIPs')+'; no qualification granted');return;}
 const mode=process.env.MATH_PROFILE,phase=process.env.NATIVE_PHASE;
 if(!['automatic','sse2'].includes(mode)||!plan.phases.includes(phase)) throw Error('Exact full direct build pair required');
 const spec=plan.cohorts[phase];
 for(const configuration of ['Debug','Release']){
  const profile=configuration+'-'+mode,[run_id,job_id,artifact_id,size,digest]=spec.pins[profile],source=await record(run_id),artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
  if(source.run.head_sha!==spec.source||source.run.run_attempt!==1||source.run.status!=='completed'||source.run.conclusion!=='success'||source.run.head_branch!==spec.branch+profile.toLowerCase()+spec.suffix||source.run.path!==spec.workflow||
     source.jobs.length!==2||source.jobs.some(j=>j.run_id!==run_id||j.head_sha!==spec.source||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))||source.jobs.filter(j=>j.id===job_id).length!==1||
     artifact.id!==artifact_id||artifact.name!==spec.artifact+profile||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest) throw Error('Exact compiled native cohort/profile/source bytes required');
  await retain('out/native-matrix-native-inputs/'+profile+'-'+phase,source,artifact);
 }
 const scalar=await record(42537676857),artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:13639682979})).data;
 if(scalar.run.head_sha!=='6f7fe42c71e30ddb4f3fa80425c3779ef1ba82ea'||scalar.run.run_attempt!==1||scalar.run.status!=='completed'||scalar.run.conclusion!=='success'||artifact.id!==13639682979||artifact.size_in_bytes!==3935729||artifact.digest!=='sha256:7812112f08d08dfb1d4540e644a54613b516fc4af6f9be8dd7384e19bc190185') throw Error('Exact independently proven scalar required');
 await retain('out/native-matrix-scalar',scalar,artifact);
 core.info('Verified full physical phase report ZIPs, exact actual native build observations and original scalar on GitHub only; no builds or recapture');
};
