// Require the real positive full-restoration route before any new capture starts.
module.exports=async ({github,context,core})=>{
  const fs=require('fs'),{owner,repo}=context.repo;
  if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)
    throw Error('Exact already-public repository required');
  const run_id=42579896898,source='23617a96d357d951dddfaac2074ebad4ce73db61';
  const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id})).data;
  const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id,per_page:100});
  const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:13656713095})).data;
  if(run.id!==run_id||run.head_sha!==source||run.head_branch!=='qualification/original-retry-reference-check-v1'||
     run.path!=='.github/workflows/phase6-original-retry-reference.yml'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='success'||
     jobs.length!==1||jobs[0].id!==129035883514||jobs[0].head_sha!==source||jobs[0].status!=='completed'||jobs[0].conclusion!=='success'||
     !jobs[0].labels.includes('ubuntu-24.04')||jobs[0].labels.includes('self-hosted')||
     artifact.id!==13656713095||artifact.expired||artifact.size_in_bytes!==4197353||
     artifact.digest!=='sha256:ef5a1fa1164f1e7d19b3a03078a2b19fe401d70eceb42315f84bb357d3a69fca'||
     artifact.workflow_run.id!==run_id||artifact.workflow_run.head_sha!==source)
    throw Error('Exact successful full retry reference restoration and source artifact required');
  for(const name of ['Preserve every original control and strict source guard',
                    'Retain exact completed audit attempts and all four original API ZIPs on GitHub only',
                    'Independently restore all 608 audited original captures without changing their provenance',
                    'Run actions/upload-artifact@v7']){
    const selected=jobs[0].steps.filter(s=>s.name===name);
    if(selected.length!==1||selected[0].status!=='completed'||selected[0].conclusion!=='success')
      throw Error('Actual full retry reference step incomplete: '+name);
  }
  fs.mkdirSync('out',{recursive:true});
  fs.writeFileSync('out/exact-retry-reference-readiness.json',JSON.stringify({repository:context.repo,run,jobs,artifact,qualification_granted:false},null,2),{flag:'wx'});
  core.setOutput('audit_run_id','42572661826');
};
