// Verify only an explicitly completed full SDK cohort; preserve every other actual run/job status.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,mode=process.env.MATH_PROFILE;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/Closeout/full-SDK-published-inputs-v1.lock.json','utf8')),pin=lock.cohorts[mode];
 if(owner!==lock.repository.owner||repo!==lock.repository.repo||!pin||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact public completed SDK cohort required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:lock.run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:lock.run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.artifact_id})).data;
 const base='out/full-SDK-published/'+mode;fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==lock.run_id||run.head_sha!==lock.source||run.head_branch!==lock.branch||run.path!==lock.workflow||run.run_attempt!==1||jobs.length!==2||new Set(jobs.map(j=>j.id)).size!==2||
    jobs.some(j=>lock.jobs[j.id]!==j.name||j.run_id!==lock.run_id||j.head_sha!==lock.source||JSON.stringify(j.labels)!==JSON.stringify(['ubuntu-24.04']))||
    !jobs.some(j=>j.id===pin.job_id&&j.status==='completed'&&j.conclusion==='success')||artifact.id!==pin.artifact_id||artifact.expired||artifact.name!=='full-original-native-SDK-variants-'+mode||
    artifact.size_in_bytes!==pin.archive_bytes||artifact.digest!=='sha256:'+pin.archive_sha256||artifact.workflow_run.id!==lock.run_id||artifact.workflow_run.head_sha!==lock.source)throw Error('Exact complete source-bound published SDK cohort required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==pin.archive_bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==pin.archive_sha256)throw Error('Actual published SDK cohort ZIP differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});core.info('Retained full published SDK/source witness metadata on GitHub only; no simulator or local bulk transfer');
};
