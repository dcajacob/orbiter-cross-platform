// Re-audit fixed existing actual observations; preserve the original failed reader status.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,c=process.env.CONFIGURATION;
 const pins={Debug:[129488509539,13716298901,4256069,'90fcf54a1a7fee0caabbf722aed70870c6be44fec0d01668cc084a1219290ddd'],Release:[129488509553,13716124351,4124978,'e7ec93daf0ac6f63f67d0e5f53d210cac17e12a8ebd4e53e0f1924985a008ae4']};
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!pins[c])throw Error('Exact existing API capture configuration required');
 const run_id=42713286498,head='8ad65617139767cba1e8fe92ef47bfedab6edd09',[job_id,artifact_id,size,digest]=pins[c];
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data,selected=jobs.filter(j=>j.id===job_id),base='out/published-Windows-api-source/'+c;
 fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.head_sha!==head||run.head_branch!=='qualification/current-windows-general-api-v3'||run.path!=='.github/workflows/phase6-current-windows-general-api.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='failure'||
    selected.length!==1||selected[0].head_sha!==head||selected[0].status!=='completed'||selected[0].conclusion!=='failure'||!selected[0].labels.includes('windows-2025')||selected[0].labels.includes('self-hosted')||
    artifact.id!==artifact_id||artifact.expired||artifact.name!=='hosted-current-Windows-GeneralApi-'+c||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact actual completed capture and failed-reader status required without normalization');
 const steps=selected[0].steps;
 for(const [name,status] of [['Execute all eight actual original corrected and observer-off-on cases in the inherited session','success'],['Independently re-read all unchanged original API assertions and exact SDK compiler source receipts','failure'],['Run actions/upload-artifact@v7','success']]){
  const matches=steps.filter(s=>s.name===name);if(matches.length!==1||matches[0].status!=='completed'||matches[0].conclusion!==status)throw Error('Actual original capture/failed-reader/upload step differs');
 }
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual original observation ZIP digest/length differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
