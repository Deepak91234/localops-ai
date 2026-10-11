export type Agent = {id:string;name:string;role:string;purpose:string;tools:string[];source:string;status:string;enabled?:boolean};
export type Job = {id:string;agent_id:string;type:string;prompt:string;priority:string;status:string;created_at:string;started_at:string|null;completed_at:string|null;result:any;error:string|null;metrics:{queue_wait_ms?:number;processing_ms?:number;inference_latency_ms?:number;tokens?:number}};
export type Activity = {id?:string;timestamp?:string;created_at?:string;type?:string;message:string;agent_id?:string;job_id?:string;detail?:any;level?:string};
export class ApiConnectionError extends Error {
 constructor(submission=false){
  super('Cannot reach the LocalOps service. Restart LocalOps AI, then reconnect.'+(submission?' The action may already have been accepted. Check task history or the agent list before trying again; it was not automatically retried.':''));
  this.name='ApiConnectionError';
 }
}
export async function api<T=any>(path:string, body?:unknown):Promise<T>{
 const submission=body!==undefined;
 const controller=submission?undefined:new AbortController();
 const timer=controller?setTimeout(()=>controller.abort(),6000):undefined;
 let response:Response;
 let text:string;
 try{
  response=await fetch(`/api${path}`,submission?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{signal:controller?.signal});
  text=await response.text();
 }catch{
  throw new ApiConnectionError(submission);
 }finally{
  if(timer!==undefined)clearTimeout(timer);
 }
 let data:any;
 try{data=JSON.parse(text)}catch{
  if([502,503,504].includes(response.status))throw new ApiConnectionError(submission);
  throw new Error(`The local service returned an unexpected response (${response.status}). Reconnect to the running LocalOps app.`);
 }
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data.error||'Request failed'));
 return data;
}
