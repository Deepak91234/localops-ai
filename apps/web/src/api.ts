export type Agent = {id:string;name:string;role:string;purpose:string;tools:string[];source:string;source_ids?:string[];status:string;enabled?:boolean;deleted_at?:string|null};
export type KnowledgeSource = {id:string;name:string;kind:'file'|'url'|'api';filename?:string;mime_type?:string;url?:string;status:string;description?:string;bytes?:number;text_length:number;shared:boolean;agent_ids:string[];last_synced_at?:string;last_attempted_at?:string;error?:string|null;refresh_minutes:number;auth_configured?:boolean;reading_note?:string;truncated?:boolean;cached?:boolean;text_preview?:string;metadata?:Record<string,unknown>;deleted_at?:string|null;restoration_note?:string;restoration_policy?:string};
export const hasKnowledgeText = (source:KnowledgeSource)=>source.text_length>0&&(source.status==='ready'||!!source.cached);
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
export async function uploadSource(file:File,options:{name?:string;description?:string;shared:boolean;agent_ids:string[]}):Promise<KnowledgeSource>{
 const body=new FormData();body.set('file',file);body.set('name',(options.name||file.name).slice(0,120));body.set('description',options.description||'');body.set('shared',String(options.shared));body.set('agent_ids',JSON.stringify(options.agent_ids));
 let response:Response;
 try{response=await fetch('/api/sources/upload',{method:'POST',body});}catch{throw new ApiConnectionError(true);}
 const data=await response.json().catch(()=>{throw new Error('The source service returned an unexpected response. Check the library before uploading again.');});
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||'Upload failed'));
 return data;
}
