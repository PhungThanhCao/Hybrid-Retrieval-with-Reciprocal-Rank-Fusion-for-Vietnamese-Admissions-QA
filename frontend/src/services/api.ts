import type {Document,Message,Source} from '../types';
const BASE=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000';
export async function ask(question:string,history:Message[]=[]):Promise<{answer:string;sources:Source[]}>{const turns=history.slice(-12).map(({role,content})=>({role,content:content.slice(0,1500)}));const r=await fetch(`${BASE}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,history:turns})});if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail?.message||e.detail||'Không thể gửi câu hỏi.')}return r.json()}
async function request(path:string, options:RequestInit={}){const r=await fetch(`${BASE}${path}`,options);if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail?.message||e.detail||'Không thể thực hiện thao tác.')}return r.json()}
export const knowledgeApi={
  list:()=>request('/api/documents') as Promise<Document[]>,
  upload:(file:File)=>{const data=new FormData();data.append('file',file);return request('/api/ingest',{method:'POST',body:data})},
  remove:(id:string)=>request(`/api/documents/${id}`,{method:'DELETE'}),
  removeAll:()=>request('/api/documents',{method:'DELETE'})
};
