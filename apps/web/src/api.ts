export type Agent = {id:string;name:string;role:string;purpose:string;tools:string[];source:string;status:string};
export type Job = {id:string;agent_id:string;type:string;prompt:string;priority:string;status:string;created_at:string;started_at:string|null;completed_at:string|null;result:any;error:string|null;metrics:{queue_wait_ms?:number;processing_ms?:number;inference_latency_ms?:number;tokens?:number}};
export type Activity = {id?:string;timestamp?:string;created_at?:string;type?:string;message:string;agent_id?:string;level?:string};
export async function api<T=any>(path:string, body?:unknown):Promise<T>{
 const response = await fetch(`/api${path}`,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data = await response.json();
 if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data.error||'Request failed'));
 return data;
}
