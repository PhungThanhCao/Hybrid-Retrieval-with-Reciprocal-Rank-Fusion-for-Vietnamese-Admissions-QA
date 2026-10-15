import {useEffect,useRef,useState} from 'react';
import type {Message} from '../types';
import {ask} from '../services/api';
import {MessageBubble} from './MessageBubble';

const suggestions=['Các phương thức xét tuyển là gì?','Học phí ngành CNTT bao nhiêu?','Thời gian đăng ký khi nào?'];
const waiting=['Đang tìm kiếm tài liệu liên quan…','Đang đối chiếu thông tin và nguồn tham khảo…','Đang soạn câu trả lời…'];
const STORAGE_KEY='admission-chat-history-v1';
type ChatSession={id:string;title:string;updatedAt:number;messages:Message[]};
const makeId=()=>`${Date.now()}-${Math.random().toString(36).slice(2)}`;
function readSessions():ChatSession[]{try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]')}catch{return []}}

export function ChatWindow(){
  const [sessions,setSessions]=useState<ChatSession[]>(readSessions);
  const initial=sessions[0];
  const [sessionId,setSessionId]=useState(initial?.id||makeId);
  const [messages,setMessages]=useState<Message[]>(initial?.messages||[]);
  const [input,setInput]=useState(''); const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const [step,setStep]=useState(0); const [historyOpen,setHistoryOpen]=useState(false);
  const end=useRef<HTMLDivElement>(null);
  useEffect(()=>end.current?.scrollIntoView({behavior:'smooth'}),[messages,busy,step]);
  useEffect(()=>{if(!busy)return;const timer=window.setInterval(()=>setStep(s=>(s+1)%waiting.length),1100);return()=>window.clearInterval(timer)},[busy]);
  useEffect(()=>{if(!messages.length)return;const title=(messages.find(m=>m.role==='user')?.content||'Cuộc trò chuyện mới').slice(0,54);setSessions(old=>{const next=[{id:sessionId,title,updatedAt:Date.now(),messages},...old.filter(item=>item.id!==sessionId)].slice(0,30);localStorage.setItem(STORAGE_KEY,JSON.stringify(next));return next})},[messages,sessionId]);
  function newChat(){if(busy)return;setSessionId(makeId());setMessages([]);setInput('');setError('');setHistoryOpen(false)}
  function openChat(session:ChatSession){if(busy)return;setSessionId(session.id);setMessages(session.messages);setError('');setHistoryOpen(false)}
  function removeChat(id:string){setSessions(old=>{const next=old.filter(item=>item.id!==id);localStorage.setItem(STORAGE_KEY,JSON.stringify(next));return next});if(id===sessionId)newChat()}
  async function send(text=input){if(!text.trim()||busy)return;const question=text.trim(),history=messages;setInput('');setError('');setStep(0);setMessages(m=>[...m,{role:'user',content:question}]);setBusy(true);try{const r=await ask(question,history);setMessages(m=>[...m,{role:'assistant',content:r.answer,sources:r.sources}])}catch(e){setError(e instanceof Error?e.message:'Có lỗi xảy ra.')}finally{setBusy(false)}}
  return <><div className="chat-toolbar"><button className="history-button" onClick={()=>setHistoryOpen(v=>!v)}>☰ Lịch sử chat</button><button className="new-chat" onClick={newChat} disabled={busy}>＋ Cuộc trò chuyện mới</button></div>{historyOpen&&<aside className="history-panel"><div><b>Lịch sử trò chuyện</b><button onClick={()=>setHistoryOpen(false)}>×</button></div>{sessions.length===0?<p>Chưa có cuộc trò chuyện nào.</p>:sessions.map(item=><article className={item.id===sessionId?'selected':''} key={item.id}><button onClick={()=>openChat(item)}><b>{item.title}</b><small>{new Date(item.updatedAt).toLocaleString('vi-VN')}</small></button><button className="remove-history" title="Xóa" onClick={()=>removeChat(item.id)}>×</button></article>)}</aside>}<div className="chat">{messages.length===0&&<div className="welcome"><h2>Xin chào!</h2><p>Hãy hỏi về ngành học, học phí, điểm chuẩn hoặc thời hạn tuyển sinh.</p><div className="suggestions">{suggestions.map(s=><button onClick={()=>send(s)} key={s}>{s}</button>)}</div></div>}{messages.map((m,i)=><MessageBubble key={i} message={m}/>)}{busy&&<div className="message assistant waiting"><i></i><span>{waiting[step]}</span></div>}{error&&<div className="error">{error} <button onClick={()=>send(input)}>Thử lại</button></div>}<div ref={end}/></div><form onSubmit={e=>{e.preventDefault();send()}}><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Nhập câu hỏi của bạn…"/><button disabled={busy||!input.trim()}>Gửi</button></form></>}
