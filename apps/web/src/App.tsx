import {Component, Suspense, lazy, useEffect, useRef, useState, type CSSProperties, type ReactNode} from 'react';
import {Activity as ActivityIcon, ArrowRight, BookOpen, Check, CircleHelp, Cpu, Layers3, List, LoaderCircle, LockKeyhole, MessageSquare, Pause, Play, Plus, RotateCcw, ShieldCheck, Users, Wallet, X, Zap} from 'lucide-react';
import {api, ApiConnectionError, type Agent, type Job, type Activity} from './api';
import AgentPage from './AgentPage';
const World = lazy(() => import('./World'));
const ROLES = ['hr', 'finance', 'support', 'security', 'optimizer'];
const ROLE_NAMES: Record<string,string> = {hr:'HR & policy',finance:'Finance',support:'Customer support',security:'Security',optimizer:'Optimizer'};
const COLORS: Record<string,string> = {hr:'#47d7d0',finance:'#9b8cff',support:'#88b7ef',security:'#f2b866',optimizer:'#a8d390'};
const ICONS: Record<string,typeof Users> = {hr:Users,finance:Wallet,support:MessageSquare,security:ShieldCheck,optimizer:Zap};
const fmt = (value: unknown, suffix='') => typeof value === 'number' ? value.toLocaleString(undefined,{maximumFractionDigits:1}) + suffix : 'Unavailable';
const time = (value?:string) => value ? new Date(value).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}) : '—';
const route = () => {try{return location.hash.startsWith('#/agents/') ? 'agent:' + decodeURIComponent(location.hash.slice(9)) : location.hash === '#/monitor' ? 'monitor' : location.hash === '#/directory' ? 'directory' : 'world'}catch{return 'world'}};
class SceneBoundary extends Component<{children:ReactNode;onError:()=>void;retry:number},{failed:boolean}>{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true}}
  componentDidCatch(){this.props.onError()}
  componentDidUpdate(previous:{retry:number}){if(this.state.failed && previous.retry!==this.props.retry)this.setState({failed:false})}
  render(){return this.state.failed ? null : this.props.children}
}
function Status({agent}:{agent:Agent}){const state=agent.enabled===false && agent.status!=='running' ? 'paused' : agent.status; return <span className={'status status-'+state}><i/>{state}</span>}
export default function App(){
  const [agents,setAgents]=useState<Agent[]>([]),[jobs,setJobs]=useState<Job[]>([]),[events,setEvents]=useState<Activity[]>([]);
  const [health,setHealth]=useState<any>(null),[system,setSystem]=useState<any>(null),[metrics,setMetrics]=useState<any>(null);
  const [page,setPage]=useState(route),[opened,setOpened]=useState<string[]>(()=>route().startsWith('agent:')?[route().slice(6)]:[]);
  const [insights,setInsights]=useState<any>(null),[backendConnected,setBackendConnected]=useState<boolean|null>(null),[streamConnected,setStreamConnected]=useState(false);
  const [connectionError,setConnectionError]=useState(''),[error,setError]=useState(''),[reconnecting,setReconnecting]=useState(false);
  const [studio,setStudio]=useState(false),[help,setHelp]=useState(false),[listView,setListView]=useState(false);
  const [reduced,setReduced]=useState(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),[resetKey,setResetKey]=useState(0);
  const [selectedId,setSelectedId]=useState<string|null>(null),[created,setCreated]=useState<Agent|null>(null),[search,setSearch]=useState('');
  const mounted=useRef(true),refreshVersion=useRef(0),activePage=useRef(page),insightVersion=useRef(0);
  activePage.current=page;
  const reportError=(e:unknown)=>{if(e instanceof ApiConnectionError){setBackendConnected(false);setConnectionError(e.message)}else setError(e instanceof Error?e.message:String(e))};
  const loadInsights=async(id:string)=>{
    const version=++insightVersion.current;
    try{const data=await api('/agents/'+encodeURIComponent(id)+'/insights');if(mounted.current&&version===insightVersion.current&&activePage.current==='agent:'+id)setInsights(data)}
    catch(e){if(mounted.current&&version===insightVersion.current&&activePage.current==='agent:'+id)reportError(e)}
  };
  const refresh=async()=>{
    const version=++refreshVersion.current;
    try{
      const [a,j,h,m,s]=await Promise.all([api<Agent[]>('/agents'),api<Job[]>('/jobs?limit=500'),api('/health'),api('/metrics'),api('/system')]);
      if(!mounted.current||version!==refreshVersion.current)return;
      setAgents(a);setJobs(j);setHealth(h);setMetrics(m);setSystem(s);setBackendConnected(true);setConnectionError('');
      if(activePage.current.startsWith('agent:'))await loadInsights(activePage.current.slice(6));
    }catch(e){if(mounted.current&&version===refreshVersion.current)reportError(e)}
  };
  const navigate=(next:string)=>{setPage(next);setError('');location.hash=next.startsWith('agent:')?'/agents/'+encodeURIComponent(next.slice(6)):next==='world'?'/workspace':'/'+next};
  const openAgent=(id:string)=>{setOpened(values=>values.includes(id)?values:[...values,id]);setSelectedId(id);navigate('agent:'+id)};
  useEffect(()=>{
    mounted.current=true;void refresh();
    const feed=new EventSource('/api/events');
    const update=(ev:MessageEvent)=>{try{
      const data=JSON.parse(ev.data);
      if(ev.type==='agents_updated')setAgents(data);
      if(ev.type==='job_updated')setJobs(values=>[data,...values.filter(job=>job.id!==data.id)]);
      if(ev.type==='snapshot'){setAgents(data.agents);setJobs(data.jobs);setMetrics(data.metrics);setEvents(data.events.slice(-40).reverse())}
      if(ev.type==='activity'||ev.type==='security_blocked'){const item=data.event||data;if(item.message)setEvents(values=>[item,...values.filter(event=>!item.id||event.id!==item.id)].slice(0,60))}
      void refresh();
    }catch{}};
    ['snapshot','job_updated','activity','agents_updated','optimizer_updated','security_blocked'].forEach(event=>feed.addEventListener(event,update));
    feed.onopen=()=>setStreamConnected(true);feed.onerror=()=>{setStreamConnected(false);void refresh()};
    const interval=setInterval(()=>void refresh(),10000);
    const onHash=()=>{const next=route();setPage(next);if(next.startsWith('agent:'))setOpened(values=>values.includes(next.slice(6))?values:[...values,next.slice(6)])};
    window.addEventListener('hashchange',onHash);
    const onKey=(ev:KeyboardEvent)=>{if(ev.key==='Escape'){setStudio(false);setHelp(false)}};
    window.addEventListener('keydown',onKey);
    return()=>{mounted.current=false;refreshVersion.current++;insightVersion.current++;feed.close();clearInterval(interval);window.removeEventListener('hashchange',onHash);window.removeEventListener('keydown',onKey)};
  },[]);
  useEffect(()=>{setInsights(null);if(page.startsWith('agent:'))void loadInsights(page.slice(6))},[page]);
  const current=page.startsWith('agent:')?agents.find(agent=>agent.id===page.slice(6)):undefined;
  const gpu=system?.telemetry||metrics?.device||{};
  const running=jobs.filter(job=>job.status==='running').length,queued=jobs.filter(job=>job.status==='queued').length;
  const enabled=agents.filter(agent=>agent.enabled!==false).length;
  const filtered=agents.filter(agent=>(agent.name+' '+ROLE_NAMES[agent.role]+' '+agent.purpose).toLowerCase().includes(search.toLowerCase()));
  const agentGrid=(values:Agent[])=><div className="team-grid">{values.map(agent=>{const Icon=ICONS[agent.role]||Users;return <button className="team-card" key={agent.id} onClick={()=>openAgent(agent.id)} style={{'--accent':COLORS[agent.role]} as CSSProperties}><span className="team-avatar"><Icon size={25}/></span><div><span className="section-label">{ROLE_NAMES[agent.role]}</span><h3>{agent.name}</h3><p>{agent.purpose}</p><Status agent={agent}/></div><ArrowRight size={17}/></button>})}</div>;
  return <div className="app shell">
    <header className="topbar">
      <a className="brand" href="#/workspace" onClick={ev=>{ev.preventDefault();navigate('world')}}><span className="brand-mark"><Layers3 size={22}/></span><span>LocalOps <b>AI</b><small>YOUR PRIVATE WORKFORCE</small></span></a>
      <div className="connection"><i className={backendConnected===true&&health?.local_inference?.available?'online-dot':'offline-dot'}/><span>{backendConnected===false?'Local service offline':health?.local_inference?.available?'Connected to local AI':backendConnected===true?'Local model unavailable':'Connecting…'}<small>{health?.local_inference?.model||'Your GX10'}</small></span></div>
      <div className="top-actions"><span className="private-badge"><LockKeyhole size={13}/> PRIVATE BY DEFAULT</span><button className="button primary create-agent" onClick={()=>setStudio(true)} disabled={backendConnected===false}><Plus size={17}/>Create agent</button></div>
    </header>
    <aside className="sidebar">
      <span className="sidebar-caption">WORKSPACE</span>
      {[['world','Living workspace',Layers3],['directory','All agents',Users],['monitor','System monitor',ActivityIcon]].map(([key,label,Icon]:any)=><button key={key} aria-label={label+(key==='directory'?' '+agents.length:'')} title={label} className={'nav-item '+(page===key?'active':'')} onClick={()=>{if(key==='directory')setSearch('');navigate(key)}}><Icon size={19}/><span>{label}</span>{key==='directory'&&<b>{agents.length}</b>}</button>)}
      <div className="sidebar-team"><span className="sidebar-caption">YOUR TEAM</span>{ROLES.map(role=>{const Icon=ICONS[role];const values=agents.filter(agent=>agent.role===role);return <button key={role} aria-label={ROLE_NAMES[role]+' '+values.length} title={ROLE_NAMES[role]} className="nav-item" onClick={()=>{if(values.length===1)openAgent(values[0].id);else{setSearch(ROLE_NAMES[role]);navigate('directory')}}}><Icon size={17} style={{color:COLORS[role]}}/><span>{ROLE_NAMES[role]}</span><b>{values.length}</b></button>})}</div>
      <div className="sidebar-bottom"><div className="local-machine"><Cpu size={19}/><span>NVIDIA GB10<small>Inference on your device</small></span></div><button className="nav-item" onClick={()=>setHelp(true)}><CircleHelp size={18}/>Quick guide</button></div>
    </aside>
    <main className="shell-main">
      <nav className="workspace-tabs" aria-label="Open workspaces">
        <button className={page==='world'?'active':''} onClick={()=>navigate('world')}><Layers3 size={14}/>Living workspace</button>
        {opened.map(id=>{const agent=agents.find(value=>value.id===id);return <div className={'open-agent-tab '+(page==='agent:'+id?'active':'')} key={id}><button onClick={()=>openAgent(id)}>{agent?.name||'Loading agent'}</button><button className="tab-close" aria-label={'Close tab for '+(agent?.name||id)} onClick={()=>{setOpened(values=>values.filter(value=>value!==id));if(page==='agent:'+id)navigate('world')}}><X size={13}/></button></div>})}
      </nav>
      <div className="page-body">
        <section className="living-page" style={{display:page==='world'?'flex':'none'}}>
          <div className="page-heading"><div><div className="eyebrow"><span/>YOUR TEAM, AT A GLANCE</div><h1>A living workspace.</h1><p>Every character is a real agent. Select one to open its workspace.</p></div><div className="team-count"><strong>{agents.length}</strong><span>physical agents<small>{enabled} enabled · {agents.length-enabled} paused</small></span></div></div>
          <div className="workspace-summary"><span><i className="online-dot"/>{running} working</span><span>{queued} waiting</span><span><Check size={14}/>{metrics?.completed_jobs??0} tasks completed</span><span className="summary-help">Create an agent to add another teammate</span></div>
          <div className="new-world-stage">
            <div className="world-canvas" style={{display:listView?'none':'block'}}><SceneBoundary retry={resetKey} onError={()=>setListView(true)}><Suspense fallback={<div className="canvas-loading"><LoaderCircle className="spin"/>Building your workspace…</div>}><World agents={agents} selected={selectedId} onSelect={openAgent} active={page==='world'&&!listView} reducedMotion={reduced} resetKey={resetKey}/></Suspense></SceneBoundary></div>
            {listView&&<div className="world-list">{agentGrid(agents)}</div>}
            {!listView&&<div className="world-instruction">Drag to explore · Scroll to zoom · Click a teammate</div>}
            <div className="world-controls"><button aria-label="Reset camera" title="Reset camera" onClick={()=>setResetKey(value=>value+1)} disabled={listView}><RotateCcw size={16}/></button><span/><button onClick={()=>{if(listView)setResetKey(value=>value+1);setListView(value=>!value)}}>{listView?<Layers3 size={16}/>:<List size={16}/>} {listView?'3D workspace':'Agent list'}</button><span/><button aria-pressed={reduced} onClick={()=>setReduced(value=>!value)}>{reduced?<Play size={14}/>:<Pause size={14}/>} {reduced?'Motion off':'Motion on'}</button></div>
            {created&&<div className="creation-toast" role="status"><span className="toast-check"><Check size={19}/></span><div><strong>{created.name} joined your team</strong><small>A new character is now in the workspace.</small></div><button className="button" onClick={()=>openAgent(created.id)}>Open agent<ArrowRight size={14}/></button><button className="icon-button" aria-label="Dismiss new agent message" onClick={()=>setCreated(null)}><X size={15}/></button></div>}
          </div>
          <section className="workspace-activity"><div className="card-heading"><span><i className="pulse-dot"/>TEAM ACTIVITY</span><span className="muted">{backendConnected===false?'Offline':streamConnected?'Live updates':'Reconnecting'}</span></div>{events.slice(0,3).map((event,i)=><div className="activity-row" key={event.id||i}><span className="activity-time">{time(event.timestamp||event.created_at)}</span><i className={event.type?.includes('block')?'amber':'cyan'}/><span>{event.message}</span>{event.agent_id&&<button onClick={()=>openAgent(event.agent_id!)}>View<ArrowRight size={12}/></button>}</div>)}{!events.length&&<p>Your team is ready. Open an agent to run its first task.</p>}</section>
        </section>
        {page==='directory'&&<section className="directory-page"><div className="page-heading"><div><div className="eyebrow">YOUR PRIVATE TEAM</div><h1>All agents.</h1><p>A separate identity, character, and task history for every teammate.</p></div><button className="button primary" onClick={()=>setStudio(true)} disabled={backendConnected===false}><Plus size={16}/>Create agent</button></div><label className="agent-search"><Users size={18}/><input aria-label="Search agents" placeholder="Search by name or role…" value={search} onChange={event=>setSearch(event.target.value)}/>{search&&<button className="icon-button" aria-label="Clear search" onClick={()=>setSearch('')}><X size={16}/></button>}</label>{agentGrid(filtered)}{!filtered.length&&<div className="empty-panel">No agents match your search.</div>}</section>}
        {page==='monitor'&&<section className="system-page"><div className="page-heading"><div><div className="eyebrow">SHARED LOCAL COMPUTE</div><h1>Your system, in view.</h1><p>Device readings describe the whole GX10. Individual job metrics live on each agent’s page.</p></div><span className="model-pill"><Cpu size={16}/>{health?.local_inference?.model||'Local Nemotron'}</span></div><div className="metric-grid">{[['GPU utilization',fmt(gpu.gpu_utilization_percent,'%')],['Temperature',fmt(gpu.temperature_c,'°C')],['Power draw',fmt(gpu.power_w,' W')],['Completed tasks',metrics?.completed_jobs??0]].map(([label,value])=><article className="metric" key={label}><span>{label}</span><strong>{value}</strong></article>)}</div><div className="notice">Shared GPU memory reporting is unavailable on GB10. Per-agent resource use is measured as tokens and job timings; it is not a GPU allocation.</div><section className="monitor-panel"><div className="card-heading"><span>RECENT TASKS</span><span>{jobs.length} saved</span></div><div className="table-scroll"><table><thead><tr><th>Agent</th><th>Task</th><th>Status</th><th>Inference</th><th>Tokens</th></tr></thead><tbody>{jobs.map(job=>{const agent=agents.find(value=>value.id===job.agent_id);return <tr key={job.id} onClick={()=>openAgent(job.agent_id)}><td><button className="text-button" onClick={()=>openAgent(job.agent_id)}>{agent?.name||job.agent_id}<ArrowRight size={13}/></button></td><td><span className="task-preview">{job.prompt}</span></td><td><span className={'status status-'+job.status}><i/>{job.status}</span></td><td>{fmt(job.metrics.inference_latency_ms,' ms')}</td><td>{fmt(job.metrics.tokens)}</td></tr>})}</tbody></table></div></section></section>}
        {current&&<AgentPage key={current.id} agent={current} reducedMotion={reduced} jobs={jobs.filter(job=>job.agent_id===current.id)} events={events} health={health} insights={insights} backendConnected={backendConnected} onRefresh={refresh} onAgentUpdate={agent=>setAgents(values=>values.map(value=>value.id===agent.id?agent:value))} onBack={()=>navigate('world')} onSelectAgent={openAgent}/>}
        {page.startsWith('agent:')&&!current&&<div className="empty-panel">{backendConnected===true?'This agent was not found.':'Loading your agent…'}<button className="button" onClick={()=>navigate('world')}>Back to workspace</button></div>}
      </div>
      {backendConnected===false&&<div className="shell-connection-error notice error" role="alert"><span>{connectionError||'The local service is offline.'}</span><button className="button" disabled={reconnecting} onClick={async()=>{setReconnecting(true);try{await refresh()}finally{setReconnecting(false)}}}><RotateCcw size={15}/>{reconnecting?'Reconnecting…':'Reconnect'}</button></div>}
      {error&&<div className="shell-connection-error notice error" role="alert">{error}<button className="icon-button" aria-label="Dismiss error" onClick={()=>setError('')}><X size={15}/></button></div>}
    </main>
    {studio&&<Studio backendConnected={backendConnected} onConnectionError={reportError} onClose={()=>setStudio(false)} onCreated={agent=>{setAgents(values=>[...values.filter(value=>value.id!==agent.id),agent]);setStudio(false);setSelectedId(agent.id);setCreated(agent);setListView(false);setResetKey(value=>value+1);navigate('world');void refresh()}}/>}
    {help&&<div className="modal-backdrop"><div className="modal guide-modal" role="dialog" aria-modal="true" aria-labelledby="guide-title"><button className="icon-button modal-close" aria-label="Close guide" onClick={()=>setHelp(false)}><X/></button><div className="eyebrow">GETTING STARTED</div><h2 id="guide-title">Meet your private AI team.</h2><p className="helper">The room is a map of your agents. Each one has its own workspace.</p>{[['Create a teammate','Choose HR, Finance, or Support. A separate character appears in the room.'],['Open its workspace','Click its character or find it in All agents. Agent pages stay open as tabs.'],['Test before trusting','Use Test agent to try a fictional request. Review its answer and cited sources.'],['Review the workload','History, resources, costs, and suggestions are scoped to that specific agent.'],['Optimize with evidence','Orbit reviews your team and Finance’s invoice findings. You decide which workers to pause.']].map(([title,body],i)=><div className="guide-step" key={title}><b>{i+1}</b><div><strong>{title}</strong><p>{body}</p></div></div>)}<p className="helper">All sample business records are fictional. Replies are drafts for review. Local costs are estimates when a rate is provided.</p></div></div>}
  </div>;
}
function Studio({backendConnected,onConnectionError,onClose,onCreated}:{backendConnected:boolean|null;onConnectionError:(error:unknown)=>void;onClose:()=>void;onCreated:(agent:Agent)=>void}){
  const [role,setRole]=useState('hr'),[name,setName]=useState(''),[purpose,setPurpose]=useState('Answer employee questions using our fictional handbook.'),[source,setSource]=useState('handbook.txt');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');const networkError=useRef(false);
  const tools:Record<string,string[]>={hr:['read_policy'],finance:['analyze_invoices'],support:['draft_support_reply']};
  const sources:Record<string,string[]>={hr:['handbook.txt','injection_policy.txt'],finance:['invoices.csv'],support:['support_playbook.txt','support_tickets.json']};
  const descriptions:Record<string,string>={hr:'Answer employee questions using our fictional handbook.',finance:'Review fictional invoices and identify duplicate and overdue records.',support:'Draft helpful customer replies using our fictional support playbook.'};
  useEffect(()=>{if(backendConnected===true&&networkError.current){networkError.current=false;setError('')}},[backendConnected]);
  const submit=async(event:React.FormEvent)=>{event.preventDefault();setError('');setBusy(true);try{const agent=await api<Agent>('/agents',{name:name.trim(),role,purpose,tools:tools[role],source});onCreated(agent)}catch(error){networkError.current=error instanceof ApiConnectionError;if(networkError.current)onConnectionError(error);setError((error as Error).message)}finally{setBusy(false)}};
  return <div className="modal-backdrop"><form className="modal studio-modal" role="dialog" aria-modal="true" aria-labelledby="studio-title" onSubmit={submit}><button type="button" className="icon-button modal-close" aria-label="Close agent studio" onClick={onClose}><X/></button><div className="eyebrow">GROW YOUR TEAM</div><h2 id="studio-title">Create a new teammate.</h2><p className="helper">Every agent gets its own character, history, and workspace.</p><div className="template-options">{['hr','finance','support'].map(value=>{const Icon=ICONS[value];return <button type="button" key={value} aria-pressed={role===value} className={role===value?'selected':''} onClick={()=>{setRole(value);setSource(sources[value][0]);setPurpose(descriptions[value])}}><Icon size={22}/>{ROLE_NAMES[value]}</button>})}</div><label>Agent name<input required minLength={2} maxLength={60} placeholder={role==='support'?'e.g. Avery — Customer care':'Give your teammate a name'} value={name} onChange={event=>setName(event.target.value)}/></label><label>What should it help with?<textarea required minLength={8} maxLength={500} rows={3} value={purpose} onChange={event=>setPurpose(event.target.value)}/></label><label>Knowledge source<select value={source} onChange={event=>setSource(event.target.value)}>{sources[role].map(value=><option key={value} value={value}>{value==='support_playbook.txt'?'Customer support playbook':value==='handbook.txt'?'Employee handbook':value==='invoices.csv'?'Invoice ledger':value==='support_tickets.json'?'Support tickets + playbook':'Security test document'}</option>)}</select></label><div className="studio-source-note"><BookOpen size={17}/><span>{role==='support'?'Includes account access, billing questions, onboarding, escalation, and privacy rules.':'Uses local fictional records. Your agent can only use its approved role tools.'}</span></div><div className="studio-tools"><ShieldCheck size={15}/><span>Approved capability: {tools[role][0].replaceAll('_',' ')}</span></div>{error&&<div className="notice error" role="alert">{error}</div>}<button className="button primary full" disabled={busy||backendConnected===false||name.trim().length<2}>{busy?<LoaderCircle size={16} className="spin"/>:<Plus size={17}/>} {busy?'Adding your teammate…':'Create agent'}</button></form></div>;
}
