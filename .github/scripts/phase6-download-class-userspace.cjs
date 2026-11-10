// Fetch only the original provider input for one package-only readiness preflight.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact existing public repository required');
 const run_id=42528403133,head='60ba46377f236c2d4705f444c0174e0f5af8252f',artifact_id=13636482999;
 const size=164848563,digest='6304d1701c0fc0775b80046d1ed3aa813b07313207027046d9a026be4f1dfe9e';
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
 const base='out/native-api-source/providers';fs.mkdirSync(base,{recursive:true});
 fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==run_id||run.head_sha!==head||run.head_branch!=='qualification/native-providers-retry'||run.path!=='.github/workflows/phase6-native-providers.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
    artifact.id!==artifact_id||artifact.name!=='native-stock-runtime-providers'||artifact.expired||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head)throw Error('Exact original provider API/source required');
 require('./phase6-download-native-api-inputs.cjs').validateJobs('providers',run,jobs);
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Exact actual provider archive differs');
 fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 core.info('Original provider input retained for one package preflight; no simulator or local transfer');
};
