// Retain the two real audit attempts and their exact original source cohort.
// This runs only on a standard GitHub runner; it never normalizes API metadata.
module.exports = async ({github,context,core}) => {
  const fs=require('fs'),crypto=require('crypto');
  const {owner,repo}=context.repo;
  const fail=message=>{throw Error(message);};
  if (owner!=='dcajacob' || repo!=='orbiter-cross-platform' || (await github.rest.repos.get({owner,repo})).data.private)
    fail('Exact already-public repository required');
  const run_id=42572661826,source='a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7';
  const pins=[
    {attempt:1,job:129013339394,id:13653861871,bytes:504023,sha:'27a7bb25c20f123eb43a3c29e5d9863045c91729a1016d2c56edd706f416a417',conclusion:'failure',stem:'first'},
    {attempt:2,job:129017134966,id:13655952217,bytes:1591965,sha:'c4fe019b60cf001be2425cc0bf69a496baea0bd6edd7b86d172632e03cdb6e4b',conclusion:'success',stem:'audit'}
  ];
  const directory='out/reference-api';fs.mkdirSync(directory,{recursive:true});
  async function download(artifact,path) {
    const response=await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'});
    const bytes=Buffer.from(response.data);
    if (bytes.length!==artifact.size_in_bytes || 'sha256:'+crypto.createHash('sha256').update(bytes).digest('hex')!==artifact.digest)
      fail('Exact API artifact length/digest differs: '+artifact.id);
    fs.writeFileSync(path,bytes,{flag:'wx'});
  }
  for (const pin of pins) {
    const run=(await github.request('GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}',{owner,repo,run_id,attempt_number:pin.attempt})).data;
    const jobs=(await github.request('GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs',{owner,repo,run_id,attempt_number:pin.attempt,per_page:100})).data.jobs;
    const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin.id})).data;
    if (run.id!==run_id || run.run_attempt!==pin.attempt || run.head_sha!==source || run.head_branch!=='qualification/original-source-audit-v2' ||
        run.path!=='.github/workflows/phase6-original-source-audit.yml' || run.status!=='completed' || run.conclusion!==pin.conclusion ||
        jobs.length!==1 || jobs[0].id!==pin.job || jobs[0].status!=='completed' || jobs[0].conclusion!==pin.conclusion ||
        !jobs[0].labels.includes('ubuntu-24.04') || jobs[0].labels.includes('self-hosted') ||
        artifact.id!==pin.id || artifact.expired || artifact.size_in_bytes!==pin.bytes || artifact.digest!=='sha256:'+pin.sha ||
        artifact.name!=='source-complete-original-stock-independent-audit' || artifact.workflow_run.id!==run_id || artifact.workflow_run.head_sha!==source)
      fail('Exact immutable audit attempt/source/job/artifact required: '+pin.attempt);
    fs.writeFileSync(directory+'/'+pin.stem+'.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
    await download(artifact,directory+'/'+pin.stem+'.zip');
  }
  const response=await github.request('GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs',{owner,repo,job_id:129013339394});
  const log=typeof response.data==='string'?Buffer.from(response.data,'utf8'):Buffer.from(response.data);
  const checksum=crypto.createHash('sha256').update(log).digest('hex');
  fs.writeFileSync(directory+'/first-job.log',log,{flag:'wx'});
  if (!((log.length===80023 && checksum==='275a70063f7f44d5663cf8fb426da9734eff78af87632841888392d5613e886f') ||
        (log.length===80020 && checksum==='f1966b1e2e7f599db11e4531407bbd8af27d0b0752edda496a2a79336475ad3e')))
    fail('First failed raw job log differs from both exact known BOM transport identities');
  const original_id=42544579421,original_source='ba38a7efccb5f770e87add95f5e966aa40270756';
  const workflow_run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:original_id})).data;
  const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:original_id,per_page:100});
  const artifacts=(await github.paginate(github.rest.actions.listWorkflowRunArtifacts,{owner,repo,run_id:original_id,per_page:100}))
    .filter(a=>/^matched-clock-remaining-stock-v2-(Debug|Release)-(automatic|sse2)$/.test(a.name));
  const originalPins={
    'Debug-automatic':[13653553212,458066616,'3e5739856625b3c4bf3369774f400f9abe697942446bd2c6582296951b67d883'],
    'Debug-sse2':[13652560965,458037834,'25cdfe101de0d451c7a48cc73af67cea77a293caf426cdd07e213069b9ecf3ad'],
    'Release-automatic':[13651374693,452695529,'2cd69c0e2200bce6da0470a8dd30110e7187b8ee825bc0c4ad7033e7d5cde1af'],
    'Release-sse2':[13650739038,452683615,'4b5a473526438476ba25b46b376e6c30727b2af37892629bd1b3116f4c398022']
  };
  if (workflow_run.id!==original_id || workflow_run.head_sha!==original_source || workflow_run.run_attempt!==1 ||
      workflow_run.status!=='completed' || workflow_run.conclusion!=='success' || jobs.length!==5 ||
      jobs.some(j=>j.head_sha!==original_source || j.status!=='completed' || j.conclusion!=='success') || artifacts.length!==4)
    fail('Exact complete unchanged original cohort required');
  const profiles=new Set();
  for (const artifact of artifacts) {
    const profile=artifact.name.replace('matched-clock-remaining-stock-v2-',''),pin=originalPins[profile];
    if (!pin || profiles.has(profile) || artifact.id!==pin[0] || artifact.size_in_bytes!==pin[1] || artifact.digest!=='sha256:'+pin[2] ||
        artifact.expired || artifact.workflow_run.id!==original_id || artifact.workflow_run.head_sha!==original_source)
      fail('Exact original profile API artifact required: '+profile);
    profiles.add(profile);
  }
  fs.writeFileSync(directory+'/original.json',JSON.stringify({workflow_run,jobs,artifacts},null,2),{flag:'wx'});
  fs.mkdirSync('out/original-stock-audit/archives',{recursive:true});
  for (const artifact of artifacts) await download(artifact,'out/original-stock-audit/archives/'+artifact.name+'.zip');
  core.info('Retained exact successful audit, preserved first failure and all four original API ZIPs on GitHub only');
};
