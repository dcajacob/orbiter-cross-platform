// Preserve completed writers and authenticate the selected profile's raw source bytes.
module.exports=async ({github,context,core})=>{
  const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
  if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact already-public repository required');
  const producer='9edaec08fbc41a25dc6cd4d319a14c950fdd8177',pins={"Debug-automatic":[42556975058,128964915249,13657036771,736116240,"c00df4086fe107a79ef87d08b2abac56ee9fa7ab1fd059130902cbd9f479bb90"],"Debug-sse2":[42556645824,128963912109,13655200082,735672583,"bd8c9078f5b85971f14acbb833cebcdbbafb406a09d190d8dd78252f2374c0d5"],"Release-automatic":[42558052729,128968217162,13656707649,736291319,"9a24896010ffd0d3947b4582ecb0945c1b6dd181566f19a8348c96f266e0be67"],"Release-sse2":[42556648122,128963912091,13656181152,735852648,"63987945a8c17d3d47635bb9ed6988c5ec9cb45ce36ca2b6287b7393bd3e6ebc"]};
  const selected=process.env.PROFILE;if(!pins[selected]) throw Error('Exact native profile required');
  const records=[];
  for(const [profile,pin] of Object.entries(pins)){
    const [run_id,job_id,artifact_id,size,digest]=pin;
    const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
    const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
    const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id})).data;
    if(run.id!==run_id||run.head_sha!==producer||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
       run.head_branch!=='qualification/native-runtime-writer-'+profile.toLowerCase()+'-v2'||run.path!=='.github/workflows/phase6-native-runtime-network-writers.yml'||
       jobs.length!==2||jobs.some(j=>j.run_id!==run_id||j.head_sha!==producer||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))||
       jobs.filter(j=>j.id===job_id).length!==1||artifact.id!==artifact_id||artifact.expired||artifact.name!=='normal-native-runtime-stock-writer-'+profile||
       artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==producer)
      throw Error('All four exact completed native writer API/source identities required: '+profile);
    records.push({repository:context.repo,run,jobs,artifact});
  }
  const base='out/native-writer-evidence/'+selected;fs.mkdirSync(base,{recursive:true});
  fs.writeFileSync('out/native-writer-evidence/all-api.json',JSON.stringify(records,null,2),{flag:'wx'});
  const record=records.find(r=>r.artifact.name==='normal-native-runtime-stock-writer-'+selected);
  fs.writeFileSync(base+'/api.json',JSON.stringify(record,null,2),{flag:'wx'});
  const response=await github.rest.actions.downloadArtifact({owner,repo,artifact_id:record.artifact.id,archive_format:'zip'}),bytes=Buffer.from(response.data);
  if(bytes.length!==record.artifact.size_in_bytes||'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==record.artifact.digest)
    throw Error('Actual retained native writer raw API ZIP length/digest differs');
  fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
  core.info('Retained exact completed native writer '+selected+' raw API ZIP on GitHub only; no writer rerun');
};
