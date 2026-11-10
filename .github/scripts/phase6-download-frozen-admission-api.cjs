// The admission consumer uses the completed independent reference, never a current job's mutable result.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 const lock=JSON.parse(fs.readFileSync('Tests/Production/Closeout/phase6-current-candidate.lock.json','utf8'));
 const p=lock.identities.reference.joint_api,run_id=p.run_id,artifact_id=p.artifact_id;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact existing public repository required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
 const base='out/frozen-admission-api';fs.mkdirSync(base,{recursive:true});
 fs.writeFileSync(base+'/api.json',JSON.stringify({repository:{owner,repo},run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==run_id||run.head_sha!==p.source||run.head_branch!=='qualification/joint-general-api-v1'||run.path!=='.github/workflows/phase6-joint-general-api.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    jobs.length!==2||new Set(jobs.map(j=>j.name)).size!==2||jobs.some(j=>!['Joint original API qualification','Independently restore and reproduce joint API qualification'].includes(j.name)||j.run_id!==run_id||j.head_sha!==p.source||j.status!=='completed'||j.conclusion!=='success'||JSON.stringify(j.labels)!=='["ubuntu-24.04"]')||
    artifact.id!==artifact_id||artifact.name!=='independently-verified-joint-GeneralApi-reference'||artifact.expired||artifact.size_in_bytes!==p.bytes||artifact.digest!=='sha256:'+p.sha256||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==p.source)
   throw Error('Exact completed independent General API reference required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==p.bytes||crypto.createHash('sha256').update(bytes).digest('hex')!==p.sha256)throw Error('Published independent API proof bytes differ');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
