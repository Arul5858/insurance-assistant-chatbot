const form = document.getElementById('chatForm');
const input = document.getElementById('messageInput');
const messages = document.getElementById('chatMessages');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
function addMessage(role, text, source='') {
  const row = document.createElement('div'); row.className = `message-row ${role === 'user' ? 'user-row' : 'bot-row'}`;
  const bubble = document.createElement('div'); bubble.className = `message-bubble ${role === 'user' ? 'user-bubble' : 'bot-bubble'}`;
  bubble.textContent = text;
  if (source && role === 'assistant') { const meta = document.createElement('div'); meta.className='message-meta'; meta.textContent = source === 'faq' ? 'FAQ answer' : source === 'ai' ? 'AI-generated response' : 'General assistant'; bubble.appendChild(meta); }
  row.appendChild(bubble); messages.appendChild(row); messages.scrollTop = messages.scrollHeight;
}
function typing(show) { const old=document.getElementById('typing'); if(old) old.remove(); if(show){const el=document.createElement('div');el.id='typing';el.className='typing';el.textContent='Assistant is typing...';messages.appendChild(el);messages.scrollTop=messages.scrollHeight;} }
async function sendMessage(text) {
  const value=(text||'').trim(); if(!value) return; addMessage('user',value); input.value=''; sendBtn.disabled=true; typing(true);
  try { const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:value})}); const data=await res.json(); typing(false); if(!res.ok) throw new Error(data.error||'Unable to send message.'); addMessage('assistant',data.reply,data.source); }
  catch(e){typing(false);addMessage('assistant',e.message||'Something went wrong.');} finally {sendBtn.disabled=false;input.focus();}
}
form.addEventListener('submit',e=>{e.preventDefault();sendMessage(input.value);});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
document.querySelectorAll('.suggestion-chip').forEach(b=>b.addEventListener('click',()=>sendMessage(b.textContent)));
newChatBtn.addEventListener('click',async()=>{await fetch('/api/new-chat',{method:'POST'});messages.innerHTML='';addMessage('assistant','New conversation started. How can I help you?');});
async function loadHistory(){try{const res=await fetch('/api/history');const data=await res.json();if(data.messages?.length){messages.innerHTML='';data.messages.forEach(m=>addMessage(m.role,m.message,m.source));}}catch(e){/* Keep greeting visible. */}}
loadHistory();
