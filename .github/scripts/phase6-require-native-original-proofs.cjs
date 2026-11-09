// Require all four actual independent raw-member/original-save proofs before physical audit.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private) throw Error('Exact existing public repository required');
 const pins=[[42614476852,"bb7ad26574ef026761c4a3c5281afe67c7bd2df3","qualification/native-reload-receipts-release-sse2-v1",".github/workflows/phase6-native-reload-receipts.yml",1,[[13672137027,112682,"4e944479ef58d9caaf468c941ae4cd179dfc6426625e320d4a08605feeb610d2","native-reload-raw-receipts-Release-sse2"]]],[42618324624,"c80af8272e0393e7ac528bb878c67d44464d534c","qualification/native-reload-receipts-second-cohort-v1",".github/workflows/phase6-native-reload-receipts-second.yml",2,[[13673846226,112810,"bb3fa6c551f675ad587536a0d202d7575ec195156fc7721bb212aeea505a35c4","native-reload-raw-receipts-Debug-sse2"],[13673508338,113014,"e722cfa9cee0f287f7039c010f2bbaeb709b9af8d9d0842f5903081fc512d16c","native-reload-raw-receipts-Release-automatic"]]],[42619733987,"f6f50d79153968b44c1a68da5e6c1e6bd56754cb","qualification/native-reload-receipts-debug-automatic-v1",".github/workflows/phase6-native-reload-receipts-final.yml",1,[[13674950659,112921,"e791e270ac866b7b00821ea1578c5ac80b559edbb31a19a54f7a3953aff41d4f","native-reload-raw-receipts-Debug-automatic"]]]],records=[];
 for(const [run_id,source,branch,path,count,artifacts] of pins){
  const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data,jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
  if(run.id!==run_id||run.head_sha!==source||run.head_branch!==branch||run.path!==path||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||jobs.length!==count||jobs.some(j=>j.run_id!==run_id||j.head_sha!==source||j.status!=='completed'||j.conclusion!=='success'||!j.labels.includes('ubuntu-24.04')||j.labels.includes('self-hosted'))) throw Error('Every actual complete native retained-byte proof required');
  const retained=[];
  for(const [id,size,digest,name] of artifacts){const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:id})).data;if(artifact.id!==id||artifact.expired||artifact.name!==name||artifact.size_in_bytes!==size||artifact.digest!=='sha256:'+digest||artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==source) throw Error('Exact independently verified raw-member proof artifact required');retained.push(artifact);}
  records.push({repository:context.repo,run,jobs,artifacts:retained});
 }
 fs.mkdirSync('out',{recursive:true});fs.writeFileSync('out/native-original-proof-readiness.json',JSON.stringify({records,qualification_granted:false},null,2),{flag:'wx'});
 core.info('All four real native raw-member/original-save proof identities retained; physical comparisons still required');
};
