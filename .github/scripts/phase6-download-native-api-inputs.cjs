// Download only existing source-bound native application and provider inputs on GitHub.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact existing public repository required');
 const native={"Debug-automatic":[13633027534,82517672,"368c2d78c0313d2a183affd72dcd98505981b42d5f4baa0ce1c9fb6cb18c95c9"],"Debug-sse2":[13633311229,82507652,"11f150fffd8b02bf6f9d438a4aff9b37a203c2d9db4eea8ae2905ff078d2898f"],"Release-automatic":[13633298021,73311503,"2d73a7a714adbac8a2824ade476255c2ad10c9a4aa7ded636ee14e5ee69f7c4b"],"Release-sse2":[13633576478,73283475,"3d9b820b9dfd9cbdc5d83357f00942659d1ef915a6fe6a0d0c286ef6a52855b4"]};
 const profile=process.env.PROFILE;if(!native[profile])throw Error('Exact native API profile required');
 for(const [role,run_id,head,artifact_id,size,digest,failed] of [
  ['native',42519601899,'ccc02c8a34bd1f227624d8778a141e8736ae8111',...native[profile],true],
  ['providers',42528403133,'60ba46377f236c2d4705f444c0174e0f5af8252f',13636482999,164848563,'6304d1701c0fc0775b80046d1ed3aa813b07313207027046d9a026be4f1dfe9e',false],
  ['mesa',42543636813,'6d17e4f18e4eade72fa295c3d03a38a58182d35f',13642189340,53687675,'7a2b06da0b1d39153066414d8ea303cdfafcbe8184170e9e80bc33cee6d61392',false]]){
  const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
  const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
  const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
  if(run.id!==run_id||run.head_sha!==head||run.run_attempt!==1||run.status!=='completed'||run.conclusion!==(failed?'failure':'success')||
     artifact.id!==artifact_id||artifact.expired||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||
     artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==head||!jobs.length||
     jobs.some(j=>!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted')||j.status!=='completed'))throw Error('Exact completed native API source/API identity required: '+role);
  const base='out/native-api-source/'+role;fs.mkdirSync(base,{recursive:true});
  fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
  const source={run,jobs};
  const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source,artifact,base,core})).data);
  if(bytes.length!==size||crypto.createHash('sha256').update(bytes).digest('hex')!==digest)throw Error('Exact original API ZIP digest/length differs');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
 core.info('Retained only exact native runtime/provider inputs; no local download, build, stock recapture or qualification');
};
