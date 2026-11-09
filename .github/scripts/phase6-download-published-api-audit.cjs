// Exact completed read-only Windows audit; no capture, SDK rebuild or API relabeling.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,c=process.env.CONFIGURATION;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!['Debug','Release'].includes(c))throw Error('Exact repository/configuration required');
 const run_id=42719673631,source='ee3c61df1a5f829485aba7cf7517ea08a3f0861c';
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifacts=await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id,per_page:100});
 const selected=jobs.filter(j=>j.name==='Reaudit existing Windows API '+c),found=artifacts.filter(a=>a.name==='published-Windows-GeneralApi-reaudit-'+c&&!a.expired);
 if(run.id!==run_id||run.head_sha!==source||run.head_branch!=='qualification/current-windows-general-api-reaudit-v3'||run.path!=='.github/workflows/phase6-current-windows-general-api-reaudit.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    jobs.length!==3||jobs.some(j=>j.head_sha!==source||j.run_id!==run_id||j.status!=='completed'||j.conclusion!=='success'||j.labels.includes('self-hosted')||!j.labels.includes(j.name==='readiness'?'ubuntu-24.04':'windows-2025'))||
    selected.length!==1||found.length!==1)throw Error('Complete exact passed read-only Windows audit run required');
 const pins={"Debug":[129510432132,13720470280,2052096,"6526027f41fb49c9522c7fd1c82baee011db2043c628008737c0b6075c15f13e"],"Release":[129510432125,13718879679,1890617,"f53c525b0e33d2f48ff340ce68648e70626a36c315f47e7d2921f4d448653df4"]};
 const [job_id,artifact_id,size,digest]=pins[c];if(selected[0].id!==job_id||found[0].id!==artifact_id||found[0].size_in_bytes!==size||found[0].digest!=='sha256:'+digest)throw Error('Exact published audit job/artifact/size/digest required');
 const artifact=found[0],base='out/published-Windows-api-audit/'+c;fs.mkdirSync(base,{recursive:true});
 fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==source||artifact.size_in_bytes>=16*1024**2)throw Error('Bounded immutable audit artifact required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)throw Error('Published audit ZIP size/digest differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
