// Disposable mock transport controls; no artifact, simulator or qualification acceptance credit.
module.exports=async ({core})=>{
 const download=require('./phase6-download-bound-artifact.cjs'),results=[];
 const check=(value,message)=>{if(!value)throw Error(message);};
 function fixture(sequence){
  const files=new Map(),calls=[],responses=sequence.slice();
  const fs={existsSync:p=>files.has(p),writeFileSync:(p,data,options)=>{if(options?.flag==='wx'&&files.has(p))throw Error('Existing fixture output');files.set(p,data);}};
  const source={run:{id:12,head_sha:'a'.repeat(40),run_attempt:1,repository:{full_name:'dcajacob/orbiter-cross-platform',private:false}}};
  const artifact={id:34,expired:false,size_in_bytes:3,digest:'sha256:'+'b'.repeat(64),workflow_run:{id:12,head_sha:source.run.head_sha}};
  const github={rest:{actions:{downloadArtifact:async args=>{calls.push(JSON.stringify(args));const next=responses.shift();if(next instanceof Error)throw next;return next;}}}};
  return {files,calls,args:{github,owner:'dcajacob',repo:'orbiter-cross-platform',source,artifact,base:'out/disposable',core,filesystem:fs,pause:async()=>{}}};
 }
 function failed(status){return Object.assign(Error('disposable transport '+status),{status,response:{status,data:{fixture:status}}});}
 async function failure(f){let error;try{await download(f.args);}catch(e){error=e;}check(error,'Failure fixture unexpectedly passed');return error;}
 const response={data:new Uint8Array([1,2,3])};
 let f=fixture([response]);check(await download(f.args)===response&&f.calls.length===1,'Successful transport bytes changed');results.push('successful-response-returned-without-relabeling');
 f=fixture([failed(503),response]);check(await download(f.args)===response&&f.calls.length===2&&f.calls[0]===f.calls[1],'HTTP503 changed artifact identity');
 check(f.files.has('out/disposable/download-failure-attempt-1.body'),'First failure body discarded');results.push('503-first-failure-and-identical-binding-preserved');
 f=fixture([failed(502),failed(504),response]);check(await download(f.args)===response&&f.calls.length===3&&new Set(f.calls).size===1,'502/504 bounded retry changed identity');results.push('502-504-exact-three-attempt-bound');
 f=fixture([failed(503),failed(503),failed(503),response]);await failure(f);check(f.calls.length===3&&JSON.parse(f.files.get('out/disposable/download-transport-attempts.json')).attempts.length===3,'Persistent failure exceeded bounds or lost attempts');results.push('persistent-503-stops-after-three');
 f=fixture([failed(403),response]);await failure(f);check(f.calls.length===1,'Nontransient error retried');results.push('403-never-retried');
 f=fixture([response]);f.args.artifact.workflow_run.head_sha='c'.repeat(40);await failure(f);check(f.calls.length===0,'Wrong-source artifact reached transport');results.push('wrong-source-rejected-before-download');
 f=fixture([{data:new Uint8Array([9,9,9,9])},response]);const raw=await download(f.args);check(raw.data.length!==f.args.artifact.size_in_bytes&&f.calls.length===1,'Size mismatch caused automatic retry');results.push('byte-mismatch-left-to-unchanged-caller-guards-without-retry');
 return {status:'passed-seven-exact-artifact-transport-controls-only',controls:results,qualification_granted:false,phase6_complete:false};
};
