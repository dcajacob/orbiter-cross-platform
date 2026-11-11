// Actual API/source/selected-job binding; never transfer old acceptance to this version.
module.exports=async ({github,context,core,role,profile})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const origin=JSON.parse(fs.readFileSync('Tests/Production/PhysicsV2/origins.json'))[role];
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!origin||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Explicit public versioned origin required');
 const name=role==='native'?'physics-v2-native-'+profile:'current-windows-sdk-'+profile;
 const jobName=role==='native'?'Rebuilt physics v2 native '+profile.replace('-',' '):'windows / Real Windows client '+profile+' x64';
 let run,jobs,artifacts;
 const deadline=Date.now()+30*60*1000;
 while(true){
  run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:origin.run_id})).data;
  jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:origin.run_id,per_page:100});
  if(run.head_sha!==origin.source||run.run_attempt!==1)throw Error('Active immutable producer changed');
  const pending=jobs.filter(j=>j.name===jobName);
  if(pending.length===1&&pending[0].status==='completed')break;
  if(Date.now()>deadline||run.status==='completed')throw Error('Selected original build did not complete; preserve it and do not start duplicates');
  core.info('Preserving active original build; waiting for '+jobName);
  await new Promise(resolve=>setTimeout(resolve,20000));
 }
 artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:origin.run_id,per_page:100});
 const found=artifacts.filter(a=>a.name===name),selected=jobs.filter(j=>j.name===jobName),label=role==='native'?'ubuntu-24.04':'windows-2025';
 if(run.head_sha!==origin.source||run.head_branch!==origin.branch||run.path!==origin.workflow||run.run_attempt!==1||run.repository.full_name!==owner+'/'+repo||run.repository.private||selected.length!==1||found.length!==1)throw Error('Actual immutable selected build producer required');
 const job=selected[0],artifact=found[0];
 if(job.run_id!==run.id||job.head_sha!==origin.source||job.status!=='completed'||job.conclusion!==(role==='native'?'failure':'success')||job.labels.join(',')!==label||artifact.expired||artifact.workflow_run.id!==run.id||artifact.workflow_run.head_sha!==origin.source||artifact.size_in_bytes<=0||artifact.size_in_bytes>=2*1024**3||!/^sha256:[a-f0-9]{64}$/.test(artifact.digest))throw Error('Exact actual standard selected build and preserved conclusion required');
 const base='out/physics-v2-input/'+role+'/'+profile;fs.mkdirSync(base,{recursive:true});
 const source={repository:context.repo,run,jobs,artifact,selected_job_id:job.id,physics_version:'assembly-contact-v2'};
 fs.writeFileSync(base+'/api.json',JSON.stringify(source,null,2),{flag:'wx'});
 const bytes=Buffer.from((await require('../../../.github/scripts/phase6-download-bound-artifact.cjs')({github,owner,repo,source,artifact,base,core})).data);
 if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)throw Error('Exact actual API archive size and SHA256 required');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
