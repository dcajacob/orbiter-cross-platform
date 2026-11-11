module.exports=async ({github,context,core,profile,role='native'})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const p=JSON.parse(fs.readFileSync('Tests/Production/PhysicsV2/capture-origin-v1.json'));
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform')throw Error('Exact public qualification repository required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:p.run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:p.run_id,per_page:100});
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:p.run_id,per_page:100});
 const name=role==='native'?'Fresh v2 all157normal stock '+profile:'Fresh v2 original failed scenes Windows '+profile;
 const label=role==='native'?'ubuntu-24.04':'windows-2025',artifactName=role==='native'?'physics-v2-normal-'+profile+'-raw':'physics-v2-Windows-'+profile+'-raw';
 const found=jobs.filter(j=>j.name===name),items=artifacts.filter(a=>a.name===artifactName);
 if(run.head_sha!==p.source||run.head_branch!==p.branch||run.path!==p.workflow||run.run_attempt!==1||run.repository.private||run.repository.full_name!==owner+'/'+repo||found.length!==1||items.length!==1)throw Error('Exact complete capture source and selected artifact required');
 const job=found[0],artifact=items[0];
 if(job.status!=='completed'||job.conclusion!=='success'||job.run_id!==run.id||job.head_sha!==p.source||job.labels.join(',')!==label||artifact.expired||artifact.workflow_run.id!==run.id||artifact.workflow_run.head_sha!==p.source||artifact.size_in_bytes<=0||artifact.size_in_bytes>=2*1024**3||!/^sha256:[a-f0-9]{64}$/.test(artifact.digest))throw Error('Actual successful standard source-bound capture required');
 const base='out/physics-v2-published/'+role+'/'+profile;fs.mkdirSync(base,{recursive:true});
 const source={repository:context.repo,run,jobs,artifact,selected_job_id:job.id,role,profile};fs.writeFileSync(base+'/api.json',JSON.stringify(source,null,2),{flag:'wx'});
 const bytes=Buffer.from((await require('../../../.github/scripts/phase6-download-bound-artifact.cjs')({github,owner,repo,source,artifact,base,core})).data);
 if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)throw Error('Actual published capture API length/SHA256 differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
