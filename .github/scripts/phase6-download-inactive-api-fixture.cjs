// Restore only the already-built same-SDK inactive fixture required by the original stager hash.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo,c=process.env.CONFIGURATION;
 const pins={Debug:[13637186106,1456611,'72147583cd6598216b8da351b8128758437696359efff1bc48a954df5902d81f',128881146142],Release:[13635944416,1399859,'d5f8a939957f76f2882df53b9f8d6331b0c2f7ca930218934d998fd6bcac3957',128881146178]};
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||!pins[c])throw Error('Exact original inactive fixture configuration required');
 const run_id=42529727362,head='348880c447f8d86beb75a92ec4aaf23d44df6500',[artifact_id,size,digest,job_id]=pins[c];
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data,selected=jobs.filter(j=>j.id===job_id),base='out/current-observer-download';
 fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.head_sha!==head||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||run.head_branch!=='qualification/current-stock-preparation'||run.path!=='.github/workflows/phase6-current-stock-preparation.yml'||
    selected.length!==1||selected[0].head_sha!==head||selected[0].status!=='completed'||selected[0].conclusion!=='success'||!selected[0].labels.includes('windows-2025')||selected[0].labels.includes('self-hosted')||
    artifact.id!==artifact_id||artifact.expired||artifact.name!=='current-stock-preparation-'+c||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact actual source-bound same-SDK inactive fixture required');
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Actual original inactive fixture ZIP digest/length differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
