// Job-selection regression controls only; no download, simulator or qualification credit.
module.exports=async ({core,fixture=JSON.parse(require('fs').readFileSync('Tests/Production/Closeout/native-api-producer-jobs.fixture.json','utf8'))})=>{
 const validate=require('./phase6-download-native-api-inputs.cjs').validateJobs,results=[];
 const check=(v,m)=>{if(!v)throw Error(m);};
 for(const role of ['native','providers','mesa']){
  const source=fixture.roles[role];validate(role,source.run,source.jobs);results.push('exact-actual-'+role+'-producer-roster-retained');
 }
 const changes=[
  ['missing-executed-job-rejected',f=>f.jobs.splice(0,1)],
  ['substituted-skipped-job-rejected',f=>{f.jobs.find(j=>j.conclusion==='skipped').id=123;}],
  ['self-hosted-executed-job-rejected',f=>{f.jobs[0].labels=['ubuntu-24.04','self-hosted'];}],
  ['active-executed-job-rejected',f=>{f.jobs[0].status='in_progress';}],
  ['wrong-source-executed-job-rejected',f=>{f.jobs[0].head_sha='f'.repeat(40);}],
  ['native-executed-job-cannot-be-skipped',f=>{f.jobs[0].conclusion='skipped';f.jobs[0].labels=[];}],
  ['skipped-job-cannot-claim-a-runner',f=>{f.jobs.find(j=>j.conclusion==='skipped').labels=['ubuntu-24.04'];}]
 ];
 for(const [name,mutate] of changes){
  const f=JSON.parse(JSON.stringify(fixture.roles.native));mutate(f);let rejected=false;
  try{validate('native',f.run,f.jobs);}catch(error){rejected=true;}
  check(rejected,name+' unexpectedly passed');results.push(name);
 }
 check(fixture.protocol==='disposable-helper-control-fixture-derived-from-actual-producer-API-v1'&&fixture.qualification_granted===false,'Fixture must not claim actual runtime credit');
 return {status:'passed-ten-exact-producer-job-selection-controls-only',controls:results,qualification_granted:false,phase6_complete:false};
};
