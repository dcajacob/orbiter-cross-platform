// Reuse the exact completed C08 application/SDK; only the API observer is freshly compiled.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,c=process.env.CONFIGURATION;
 const pins={Debug:[13636121355,302580954,'92feab053d8120c90f0abdfa0e90b7466fcfb0c7833b610245d4e90323ad0419'],Release:[13635896646,207768498,'079b7ad0c06dd66454a9a60697670bee370fbcca0e040a4d877e934d952dd206']};
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!pins[c])throw Error('Exact public current SDK API configuration required');
 const run_id=42525562745,head='c08f93151827949ee3ad498f8021f35c11753fde',[artifact_id,size,digest]=pins[c];
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data,selected=jobs.filter(j=>j.name==='current-windows / Real Windows client '+c+' x64');
 const base='out/current-sdk-source';fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.head_sha!==head||run.head_branch!=='qualification/current-windows-sdk-retry'||run.path!=='.github/workflows/phase6-current-windows-sdk.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    selected.length!==1||selected[0].head_sha!==head||selected[0].status!=='completed'||selected[0].conclusion!=='success'||!selected[0].labels.includes('windows-2025')||selected[0].labels.includes('self-hosted')||
    artifact.id!==artifact_id||artifact.expired||artifact.name!=='current-windows-sdk-'+c||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact closed source-bound original C08 SDK required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual current SDK API ZIP digest/length differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
