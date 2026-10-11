import {useEffect,useRef,useState} from 'react';
import {Check,FolderPlus,LoaderCircle,Plus,X} from 'lucide-react';
import {createPortal} from 'react-dom';
import {api,type AgentCategory} from './api';
import './categories.css';

const PALETTE=['#86b9e4','#47d7d0','#a99aef','#e4ba80','#9fc99b','#ea9ebc'];
export function CategoryCreator({onCreated,onCancel,onBusyChange}:{onCreated:(category:AgentCategory)=>void;onCancel:()=>void;onBusyChange?:(busy:boolean)=>void}){
 const [name,setName]=useState(''),[color,setColor]=useState(PALETTE[0]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const input=useRef<HTMLInputElement>(null);
 useEffect(()=>{input.current?.focus();},[]);
 useEffect(()=>{onBusyChange?.(busy);return()=>onBusyChange?.(false);},[busy,onBusyChange]);
 const create=async()=>{if(!name.trim()||busy)return;setBusy(true);setError('');try{onCreated(await api<AgentCategory>('/categories',{name:name.trim(),color}));}catch(cause){setError(cause instanceof Error?cause.message:String(cause));}finally{setBusy(false);}};
 return <div className="category-creator">
  <label>Category name<input ref={input} aria-label="New category name" maxLength={60} placeholder="e.g. Marketing, Operations, Research" value={name} disabled={busy} onChange={event=>setName(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();void create();}}}/></label>
  <span className="category-field-label">Workspace color</span><div className="category-palette">{PALETTE.map(value=><button type="button" key={value} aria-label={`Category color ${value}`} aria-pressed={color===value} disabled={busy} style={{background:value}} onClick={()=>setColor(value)}>{color===value&&<Check size={16}/>}</button>)}<label className="category-custom-color"><input type="color" aria-label="Choose a custom category color" value={color} disabled={busy} onChange={event=>setColor(event.target.value)}/><span>Custom</span></label></div>
  {error&&<p role="alert" className="category-error">{error}</p>}
  <div className="category-create-actions"><button type="button" className="button secondary" disabled={busy} onClick={onCancel}>Cancel</button><button type="button" className="button primary" disabled={busy||!name.trim()} onClick={()=>void create()}>{busy?<LoaderCircle className="spin" size={15}/>:<Plus size={15}/>} {busy?'Adding category…':'Add category'}</button></div>
 </div>;
}
export function CategoryDialog({onCreated,onClose}:{onCreated:(category:AgentCategory)=>void;onClose:()=>void}){
 const dialog=useRef<HTMLDivElement>(null);const [previousFocus]=useState(()=>document.activeElement as HTMLElement|null);
 useEffect(()=>{return()=>{if(previousFocus?.isConnected)previousFocus.focus();};},[previousFocus]);
 const onKeyDown=(event:React.KeyboardEvent)=>{if(event.key==='Escape'){event.stopPropagation();onClose();}if(event.key==='Tab'){const fields=Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled])')||[]).filter(item=>item.getClientRects().length);const first=fields[0],last=fields[fields.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}};
 return createPortal(<div className="modal-backdrop category-backdrop"><div ref={dialog} onKeyDown={onKeyDown} className="modal category-dialog" role="dialog" aria-modal="true" aria-labelledby="category-title"><button type="button" className="icon-button modal-close" aria-label="Close category creation" onClick={onClose}><X/></button><span className="category-dialog-icon"><FolderPlus size={25}/></span><h2 id="category-title">Give your team a category.</h2><p className="helper">Organize agents into a named group with its own color and space in the office.</p><CategoryCreator onCreated={onCreated} onCancel={onClose}/></div></div>,document.body);
}
export function CategoryPicker({categories,value,onChange,onCreated,onBusyChange}:{categories:AgentCategory[];value:string;onChange:(id:string)=>void;onCreated:(category:AgentCategory)=>void;onBusyChange?:(busy:boolean)=>void}){
 const [adding,setAdding]=useState(false);
 return <div className="studio-category"><div className="category-picker-row"><label>Team category<select aria-label="Agent category" value={value} onChange={event=>onChange(event.target.value)}>{categories.map(category=><option key={category.id} value={category.id}>{category.name}</option>)}</select></label><button type="button" className="button secondary" aria-expanded={adding} onClick={()=>setAdding(value=>!value)}><FolderPlus size={15}/>New category</button></div><p className="category-hint">Agents in the same category sit together. Their purpose and knowledge determine their work.</p>{adding&&<CategoryCreator onBusyChange={onBusyChange} onCancel={()=>setAdding(false)} onCreated={category=>{onCreated(category);onChange(category.id);setAdding(false);}}/>}</div>;
}
