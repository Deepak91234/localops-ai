import {useEffect,useId,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {LoaderCircle,Trash2,X} from 'lucide-react';
import './deletion.css';

type Props={kind:'agent'|'source';name:string;busy:boolean;error?:string;onConfirm:()=>void;onClose:()=>void};
export default function ConfirmDelete({kind,name,busy,error,onConfirm,onClose}:Props){
 const title=useId(),description=useId(),dialog=useRef<HTMLDivElement>(null),cancel=useRef<HTMLButtonElement>(null);
 const [returnFocus]=useState(()=>document.activeElement as HTMLElement|null);
 useEffect(()=>{cancel.current?.focus();return()=>{if(returnFocus?.isConnected)returnFocus.focus();};},[returnFocus]);
 const keys=(event:React.KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();if(!busy)onClose();}if(event.key==='Tab'){event.stopPropagation();const buttons=Array.from(dialog.current?.querySelectorAll<HTMLButtonElement>('button:not([disabled])')||[]);const first=buttons[0],last=buttons[buttons.length-1];if(!first){event.preventDefault();return;}if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}};
 return createPortal(<div className="delete-backdrop" onKeyDown={keys}><div ref={dialog} className="delete-dialog" role="alertdialog" aria-modal="true" aria-labelledby={title} aria-describedby={description}>
  <button type="button" className="delete-close" aria-label="Close delete confirmation" disabled={busy} onClick={onClose}><X size={19}/></button>
  <span className="delete-emblem"><Trash2 size={24}/></span><h2 id={title}>Delete {kind==='agent'?'agent':'knowledge source'}?</h2><p className="delete-name">{name}</p>
  <div id={description}>{kind==='agent'?<p>Remove this agent and its character from your workspace. Waiting tasks will be cancelled; task history and knowledge files are kept.</p>:<p>Remove this source from the library and every assigned agent. Its scheduled updates will stop. Saved task evidence stays in history.</p>}<p>You can undo this or restore it from <strong>Trash</strong>.{kind==='source'?' Restored sources are private until you choose their access.':''}</p></div>
  {error&&<div className="delete-error" role="alert">{error}</div>}
  <div className="delete-dialog-actions"><button ref={cancel} type="button" className="button" disabled={busy} onClick={onClose}>Keep {kind==='agent'?'agent':'source'}</button><button type="button" className="button delete-confirm" disabled={busy} onClick={onConfirm}>{busy?<LoaderCircle size={16} className="spin"/>:<Trash2 size={16}/>} {busy?'Deleting…':`Delete ${kind==='agent'?'agent':'source'}`}</button></div>
 </div></div>,document.body);
}
