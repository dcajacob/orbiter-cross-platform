// Reuse only exact immutable original native packages; no provider or simulator downloads.
module.exports=async ({github,context,core})=>{
 const fs=require('fs'),crypto=require('crypto'),{owner,repo}=context.repo;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||(await github.rest.repos.get({owner,repo})).data.private)throw Error('Exact existing public repository required');
 const pins={'Debug-automatic':[13633027534,82517672,'368c2d78c0313d2a183affd72dcd98505981b42d5f4baa0ce1c9fb6cb18c95c9'],'Debug-sse2':[13633311229,82507652,'11f150fffd8b02bf6f9d438a4aff9b37a203c2d9db4eea8ae2905ff078d2898f'],'Release-automatic':[13633298021,73311503,'2d73a7a714adbac8a2824ade476255c2ad10c9a4aa7ded636ee14e5ee69f7c4b'],'Release-sse2':[13633576478,73283475,'3d9b820b9dfd9cbdc5d83357f00942659d1ef915a6fe6a0d0c286ef6a52855b4']};
 const profile=process.env.PROFILE,pin=pins[profile];if(!pin)throw Error('Exact original numerical profile required');
 const run=(await github.rest.actions.getWorkflowRun({owner,repo,run_id:42519601899})).data;
 const jobs=await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:run.id,per_page:100});
 const artifact=(await github.rest.actions.getArtifact({owner,repo,artifact_id:pin[0]})).data;
 const base='out/native-math-source/'+profile;fs.mkdirSync(base,{recursive:true});fs.writeFileSync(base+'/api.json',JSON.stringify({repository:context.repo,run,jobs,artifact},null,2),{flag:'wx'});
 if(run.id!==42519601899||run.head_sha!=='ccc02c8a34bd1f227624d8778a141e8736ae8111'||run.run_attempt!==1||run.status!=='completed'||run.conclusion!=='failure'||artifact.id!==pin[0]||artifact.name!=='phase6-full-native-'+profile||artifact.expired||artifact.size_in_bytes!==pin[1]||artifact.digest!=='sha256:'+pin[2]||artifact.workflow_run.id!==run.id||artifact.workflow_run.head_sha!==run.head_sha)throw Error('Exact original failed source run and preserved native package required');
 require('./phase6-download-native-api-inputs.cjs').validateJobs('native',run,jobs);
 const bytes=Buffer.from((await require('./phase6-download-bound-artifact.cjs')({github,owner,repo,source:{run,jobs},artifact,base,core})).data);
 if(bytes.length!==pin[1]||crypto.createHash('sha256').update(bytes).digest('hex')!==pin[2])throw Error('Actual original native package ZIP differs');fs.writeFileSync(base+'/producer.zip',bytes,{flag:'wx'});
};
