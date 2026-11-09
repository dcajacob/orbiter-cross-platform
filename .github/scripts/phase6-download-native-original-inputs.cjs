// Download exact immutable retained inputs only; no build or simulation.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact existing public repository required');
 const profile=process.env.PROFILE,phase=process.env.NATIVE_PHASE;
 const cohorts={"stock-writer":{"source":"9edaec08fbc41a25dc6cd4d319a14c950fdd8177","branch":"qualification/native-runtime-writer-","suffix":"-v2","workflow":".github/workflows/phase6-native-runtime-network-writers.yml","artifact":"normal-native-runtime-stock-writer-","pins":{"Debug-automatic":[42556975058,128964915249,13657036771,736116240,"c00df4086fe107a79ef87d08b2abac56ee9fa7ab1fd059130902cbd9f479bb90"],"Debug-sse2":[42556645824,128963912109,13655200082,735672583,"bd8c9078f5b85971f14acbb833cebcdbbafb406a09d190d8dd78252f2374c0d5"],"Release-automatic":[42558052729,128968217162,13656707649,736291319,"9a24896010ffd0d3947b4582ecb0945c1b6dd181566f19a8348c96f266e0be67"],"Release-sse2":[42556648122,128963912091,13656181152,735852648,"63987945a8c17d3d47635bb9ed6988c5ec9cb45ce36ca2b6287b7393bd3e6ebc"]}},"windows-save-reload":{"source":"d2c579064f880e6c930da2263d1aa738d53e5423","branch":"qualification/native-stock-reload-","suffix":"-v3","workflow":".github/workflows/phase6-native-retry-stock-reloads.yml","artifact":"retry-native-stock-reload-","pins":{"Release-sse2":[42586898292,129058981287,13670583705,735725777,"5c9dbd9ee46711f7753ef48ea214e3039d5a5579010a2f954ea1e1fe594c8d30"],"Debug-sse2":[42586898426,129059018674,13673108137,735571099,"0eb3aa5828ee2de3892417ae0e8f310f78e07e56954d60aefe712a65e477b418"],"Release-automatic":[42586898836,129058984274,13673666999,736202018,"5897e56bedecaf591390c7f3571d88690dd60abb6bf85cdfa2f7d6165d85162b"],"Debug-automatic":[42586897811,129058969708,13673707991,736035328,"97a078c418f2a2ec4db4bc9230eaeb07642f7740c1108fa026e16c5c50935ee6"]}}};
 if(!cohorts[phase]||!cohorts[phase].pins[profile]) throw Error('Exact full native phase/profile required');
 async function record(run_id){return {run:(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs:await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100})};}
 async function download(base,source,artifact){
  if(artifact.expired||artifact.workflow_run.id!==source.run.id||artifact.workflow_run.head_sha!==source.run.head_sha) throw Error('Exact unexpired source artifact required');
  fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,...source,artifact},null,2),{flag:'wx'});
  const bytes=Buffer.from((await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'})).data);
  if(bytes.length!==artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest) throw Error('Actual immutable API ZIP length/digest differs');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
 }
 const matrix=[];let selected;
 for(const [kind,spec] of Object.entries(cohorts)) for(const [p,pin] of Object.entries(spec.pins)){
  const [run_id,job_id,artifact_id,size,digest]=pin,source=await record(run_id),run=source.run;
  const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
  const name=(kind==='stock-writer'?'Normal native runtime stock writer ':'Native exact original save reload ')+p.replace('-',' ');
  if(run.id!==run_id||run.head_sha!==spec.source||run.head_branch!==spec.branch+p.toLowerCase()+spec.suffix||run.path!==spec.workflow||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
     source.jobs.length!==2||source.jobs.some(j=>j.run_id!==run_id||j.head_sha!==spec.source||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))||
     source.jobs.filter(j=>j.id===job_id&&j.name===name).length!==1||artifact.id!==artifact_id||artifact.expired||artifact.name!==spec.artifact+p||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==spec.source) throw Error('Every exact closed writer/reload profile/source/API identity required: '+kind+'/'+p);
  matrix.push({phase:kind,profile:p,repository:context.repo,...source,artifact});if(kind===phase&&p===profile) selected={source,artifact};
 }
 fs.mkdirSync('out/native-original-source',{recursive:true});fs.writeFileSync('out/native-original-source/all-native-api.json',JSON.stringify(matrix,null,2),{flag:'wx'});
 if(!selected) throw Error('Selected exact native phase missing');await download('out/native-original-source/'+profile+'-'+phase,selected.source,selected.artifact);
 const native={"Debug-automatic":[13633027534,82517672,"368c2d78c0313d2a183affd72dcd98505981b42d5f4baa0ce1c9fb6cb18c95c9"],"Debug-sse2":[13633311229,82507652,"11f150fffd8b02bf6f9d438a4aff9b37a203c2d9db4eea8ae2905ff078d2898f"],"Release-automatic":[13633298021,73311503,"2d73a7a714adbac8a2824ade476255c2ad10c9a4aa7ded636ee14e5ee69f7c4b"],"Release-sse2":[13633576478,73283475,"3d9b820b9dfd9cbdc5d83357f00942659d1ef915a6fe6a0d0c286ef6a52855b4"]};
 const auxiliary=[['native',42519601899,'ccc02c8a34bd1f227624d8778a141e8736ae8111',...native[profile],true],
  ['providers',42528403133,'60ba46377f236c2d4705f444c0174e0f5af8252f',13636482999,164848563,'6304d1701c0fc0775b80046d1ed3aa813b07313207027046d9a026be4f1dfe9e',false],
  ['mesa',42543636813,'6d17e4f18e4eade72fa295c3d03a38a58182d35f',13642189340,53687675,'7a2b06da0b1d39153066414d8ea303cdfafcbe8184170e9e80bc33cee6d61392',false],
  ['ssim',42537676857,'6f7fe42c71e30ddb4f3fa80425c3779ef1ba82ea',13639682979,3935729,'7812112f08d08dfb1d4540e644a54613b516fc4af6f9be8dd7384e19bc190185',false]];
 for(const [role,run_id,head,artifact_id,size,digest,failed] of auxiliary){
  const source=await record(run_id),artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
  if(source.run.id!==run_id||source.run.head_sha!==head||source.run.run_attempt!==1||source.run.status!=='completed'||source.run.conclusion!==(failed?'failure':'success')||artifact.id!==artifact_id||artifact.expired||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest) throw Error('Exact separately owned runtime/provider/scalar input required: '+role);
  await download('out/native-original-auxiliary/'+role,source,artifact);
 }
 core.info('Retained exact complete native cohort API identities and selected raw phase/runtime/provider/scalar ZIPs on GitHub only; no recapture');
};
