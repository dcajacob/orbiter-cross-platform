// Re-read and download exact completed native API captures on GitHub only.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,profile=process.env.PROFILE;
 const pins={
 'Debug-automatic':[129448961099,13712350791,320264924,'388805482645bddfa827f57cd33e79dc2d5aae8c540bbb6b1128dff5595ab072'],
 'Debug-sse2':[129448960890,13712865162,320241034,'f74c4129d8bc4da547a8efcff7ff86d1564453d519fc8a1ec60f5c30abb15345'],
 'Release-automatic':[129448960802,13713145583,320274510,'641aa84ab0ad6a98cf495178738bab07324581de340c0843f7ca4d4848e8a860'],
 'Release-sse2':[129448960799,13712112855,320250511,'edefd3fd32ad99e441911fdc2e54aa601ae9b7d36f46dc53a0b2b3f5e1fdc7d1']};
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!pins[profile])throw Error('Exact native API profile/repository required');
 const run_id=42701960873,head='a75157bdec9f49b17da6ca04eb57699e16c87e8a';
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const [job_id,artifact_id,size,digest]=pins[profile],artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
 const base='out/native-api-published/'+profile;fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.head_sha!==head||run.head_branch!=='qualification/native-general-api-v2'||run.path!=='.github/workflows/phase6-native-general-api.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    jobs.length!==5||jobs.some(j=>j.head_sha!==head||j.run_id!==run_id||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))||
    jobs.filter(j=>j.id===job_id&&j.name==='Native original and corrected API '+profile.replace('-',' ')).length!==1||
    artifact.id!==artifact_id||artifact.expired||artifact.name!=='native-GeneralApi-'+profile||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact complete source-bound native API capture required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual published native API ZIP digest/length differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
