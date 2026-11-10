// Only explicitly completed original profiles are fetched; other live producer states remain recorded.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,profile=process.env.PROFILE;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/Closeout/class-capability-published-inputs-v1.lock.json','utf8')),pin=lock.profiles[profile];
 if(owner!==lock.repository.owner||repo!==lock.repository.repo||!pin||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact public original class profile required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:lock.run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:lock.run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.artifact_id})).data;
 const base='out/class-capability-published/'+profile;fs.mkdirSync(base,{recursive:true});
 fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==lock.run_id||run.head_sha!==lock.source||run.head_branch!==lock.branch||run.path!==lock.workflow||run.run_attempt!==1||
    run.status!=='completed'||run.conclusion!=='success'||jobs.length!==5||new Set(jobs.map(j=>j.id)).size!==5||
    jobs.some(j=>j.status!=='completed'||j.conclusion!=='success'||lock.jobs[j.id]!==j.name||j.head_sha!==lock.source||j.run_id!==lock.run_id||JSON.stringify(j.labels)!==JSON.stringify(['ubuntu-24.04']))||
    [lock.readiness_job_id,pin.job_id].some(id=>!jobs.some(j=>j.id===id&&j.status==='completed'&&j.conclusion==='success'))||
    artifact.id!==pin.artifact_id||artifact.expired||artifact.name!=='original-class-capability-controls-'+profile||
    artifact.size_in_bytes!==pin.archive_bytes||artifact.digest!=='sha256:'+pin.archive_sha256||
    artifact.workflow_run.id!==lock.run_id||artifact.workflow_run.head_sha!==lock.source)throw Error('Exact completed selected class profile/API/roster required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==pin.archive_bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==pin.archive_sha256)throw Error('Actual exact published class ZIP differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 core.info('Retained only completed '+profile+'; all other producer statuses remain unchanged; no local transfer or simulator');
};
