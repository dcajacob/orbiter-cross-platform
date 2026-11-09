// Retry only transient binary transport errors for the same already-bound API artifact.
// The callers retain their original exact size/SHA/source acceptance checks.
module.exports=async ({github,owner,repo,source,artifact,base,core,filesystem=require('fs'),pause=ms=>new Promise(r=>setTimeout(r,ms))})=>{
 const fs=filesystem,run=source.run;
 if(owner!=='dcajacob'||repo!=='orbiter-cross-platform'||run.repository.full_name!==owner+'/'+repo||run.repository.private!==false||
    run.run_attempt!==1||!Number.isSafeInteger(artifact.id)||artifact.id<=0||artifact.expired!==false||
    artifact.workflow_run.id!==run.id||artifact.workflow_run.head_sha!==run.head_sha||!/^[0-9a-f]{40}$/.test(run.head_sha)||
    !Number.isSafeInteger(artifact.size_in_bytes)||artifact.size_in_bytes<=0||artifact.size_in_bytes>=4*1024**3||
    !/^sha256:[0-9a-f]{64}$/.test(artifact.digest)) throw Error('Exact existing public same-source artifact transport binding required');
 const journal=base+'/download-transport-attempts.json';
 if(fs.existsSync(journal))throw Error('Fresh retained transport-attempt journal required');
 const record={artifact_id:artifact.id,source_run_id:run.id,source_head_sha:run.head_sha,source_run_attempt:run.run_attempt,
  expected_archive_bytes:artifact.size_in_bytes,expected_archive_sha256:artifact.digest,attempts:[],qualification_granted:false};
 const save=()=>fs.writeFileSync(journal,JSON.stringify(record,null,2));
 save();
 for(let attempt=1;attempt<=3;attempt++){
  try{
   const response=await github.rest.actions.downloadArtifact({owner,repo,artifact_id:artifact.id,archive_format:'zip'});
   record.attempts.push({attempt,status:'returned-unchanged-to-original-size-and-SHA-guards'});save();return response;
  }catch(error){
   const status=Number(error.status??error.response?.status),body=error.response?.data;
   const path=base+'/download-failure-attempt-'+attempt+'.body';
   const bytes=typeof body==='string'||ArrayBuffer.isView(body)?body:body instanceof ArrayBuffer?new Uint8Array(body):JSON.stringify(body??null);
   fs.writeFileSync(path,bytes,{flag:'wx'});
   record.attempts.push({attempt,status:Number.isFinite(status)?status:null,error_name:String(error.name),error_message:String(error.message),failure_body:path});save();
   if(![502,503,504].includes(status)||attempt===3)throw error;
   core.info('Preserved transient HTTP'+status+' for exact artifact '+artifact.id+'; retry '+(attempt+1)+' of 3 with identical binding');
   await pause(attempt*1000);
  }
 }
};
