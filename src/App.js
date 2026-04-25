import { useState,useEffect,useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

const API="http://localhost:5000";
const WS="ws://localhost:5000";

const VIEW_CONFIG={
chat:{label:"💬 Chat",apiType:null},
articles:{label:"📄 Articles",apiType:"article"},
videos:{label:"🎥 Videos",apiType:"video"},
books:{label:"📚 Books",apiType:"book"},
datasets:{label:"🗂 Datasets",apiType:"dataset"},
notebooks:{label:"📓 Notebooks",apiType:"notebook"},
github:{label:"💻 GitHub Repos",apiType:"github_repo"},
skillTrees:{label:"🌱 Skill Trees",apiType:"skill_tree"},
roadmaps:{label:"🛣 Roadmaps",apiType:"roadmap"},
resources:{label:"📚 Resources",apiType:"resource"}
};

export default function App(){

const [username,setUsername]=useState("");
const [password,setPassword]=useState("demo123");
const [token,setToken]=useState(
localStorage.getItem("token")||""
);

const [loggedIn,setLoggedIn]=useState(
!!localStorage.getItem("token")
);

const [view,setView]=useState("chat");

const [messages,setMessages]=useState([]);
const [thinking,setThinking]=useState([]);
const [input,setInput]=useState("");

const [connected,setConnected]=useState(false);
const [resources,setResources]=useState([]);
const [loadingResources,setLoadingResources]=useState(false);

const [loginError,setLoginError]=useState("");

const [speechSupported,setSpeechSupported]=useState(false);
const [isRecording,setIsRecording]=useState(false);

const [uploadingResume,setUploadingResume]=useState(false);
const [uploadMessage,setUploadMessage]=useState("");

const wsRef=useRef(null);
const inputRef=useRef(null);
const bottomRef=useRef(null);
const recognitionRef=useRef(null);
const fileInputRef=useRef(null);


/* ---------------- helpers ---------------- */

const authHeaders=()=>({
Authorization:`Bearer ${token}`
});


/* ---------------- login ---------------- */

const login=async()=>{

try{

setLoginError("");

const res=await fetch(
`${API}/login`,
{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
user_id:username,
password
})
}
);

const data=await res.json();

if(!data.success){
setLoginError(
data.message || "Login failed"
);
return;
}

localStorage.setItem(
"token",
data.token
);

localStorage.setItem(
"user_id",
data.user_id
);

setToken(data.token);
setUsername(data.user_id);
setLoggedIn(true);

}catch(e){
console.error(e);
setLoginError(
"Login failed"
);
}

};


const logout=async()=>{

try{

await fetch(
`${API}/logout`,
{
method:"POST",
headers:authHeaders()
}
);

}catch(e){
console.error(e);
}

localStorage.removeItem(
"token"
);
localStorage.removeItem(
"user_id"
);

setLoggedIn(false);
setToken("");
setMessages([]);
};



/* restore user */

useEffect(()=>{

const u=
localStorage.getItem(
"user_id"
);

if(u){
setUsername(u);
}

},[]);



/* ---------------- websocket ---------------- */

useEffect(()=>{

if(
!loggedIn||
!username||
!token
) return;

const ws=
new WebSocket(
`${WS}/ws/${username}?token=${token}`
);

wsRef.current=ws;

ws.onopen=()=>{
setConnected(true);
};

ws.onclose=()=>{
setConnected(false);
};

ws.onerror=()=>{
ws.close();
};

ws.onmessage=(event)=>{

try{

const data=
JSON.parse(
event.data
);

if(data.think){
setThinking(
p=>[
...p,
data.think
]
);
}

if(data.message){
setMessages(
p=>[
...p,
{
sender:"server",
text:data.message
}
]
);
}

}catch(e){
console.error(e);
}

};

return()=>{
ws.close();
};

},[
loggedIn,
username,
token
]);



/* ---------------- speech ---------------- */

useEffect(()=>{

const SR=
window.SpeechRecognition||
window.webkitSpeechRecognition;

if(!SR){
setSpeechSupported(false);
return;
}

setSpeechSupported(true);

const r=
new SR();

r.continuous=false;
r.interimResults=false;

r.onstart=()=>{
setIsRecording(true);
};

r.onend=()=>{
setIsRecording(false);
};

r.onresult=(event)=>{

let txt="";

for(
let i=0;
i<event.results.length;
i++
){
if(
event.results[i].isFinal
){
txt+=
event.results[i][0]
.transcript;
}
}

if(
txt.trim()
){
setInput(prev=>
prev
? prev+" "+txt.trim()
: txt.trim()
);
}

};

recognitionRef.current=r;

return()=>{
try{
r.stop();
}catch{}
};

},[]);


const toggleRecording=()=>{

if(
!recognitionRef.current
)return;

if(
isRecording
){
recognitionRef.current.stop();
}
else{
try{
recognitionRef.current.start();
}catch(e){
console.error(e);
}
}

};



/* ---------------- send ---------------- */

const sendMessage=()=>{

if(
!input.trim()
)return;

const ws=
wsRef.current;

if(
!ws||
ws.readyState!==1
)return;

const payload={
message:input
};

ws.send(
JSON.stringify(
payload
)
);

setMessages(
p=>[
...p,
{
sender:"user",
text:input
}
]
);

setInput("");

};



/* ---------------- resources ---------------- */

const fetchResources=
async()=>{

const apiType=
VIEW_CONFIG[view]
?.apiType;

if(!apiType)
return;

setLoadingResources(
true
);

try{

const res=
await fetch(
`${API}/get_resource_by_type/${username}/${apiType}`,
{
method:"POST",
headers:authHeaders()
}
);

const data=
await res.json();

setResources(
data.response||[]
);

}catch(e){
console.error(e);
}
finally{
setLoadingResources(
false
);
}

};


useEffect(()=>{
if(
view!=="chat"
){
fetchResources();
}
},[view]);


const archiveResource=
async(id)=>{

await fetch(
`${API}/update_resource_status/${username}/${id}`,
{
method:"POST",
headers:{
...authHeaders(),
"Content-Type":
"application/json"
},
body:JSON.stringify({
status:"archived"
})
}
);

setResources(
prev=>
prev.filter(
r=>
(r.id||
r._id||
r.resource_id)!==id
)
);

};



const deleteResource=
async(id)=>{

await fetch(
`${API}/delete_resource/${username}/${id}`,
{
method:"DELETE",
headers:authHeaders()
}
);

setResources(
prev=>
prev.filter(
r=>
(r.id||
r._id||
r.resource_id)!==id
)
);

};



/* ---------------- resume upload ---------------- */

const openResumePicker=()=>{
fileInputRef.current?.
click();
};


const handleResumeUpload=
async(e)=>{

const file=
e.target.files?.[0];

if(!file) return;

if(
file.type!=="application/pdf"
){
setUploadMessage(
"PDF only"
);
return;
}

if(
file.size>
5*1024*1024
){
setUploadMessage(
"Under 5MB only"
);
return;
}

try{

setUploadingResume(
true
);

const fd=
new FormData();

fd.append(
"file",
file
);

const res=
await fetch(
`${API}/upload_resume/${username}`,
{
method:"POST",
headers:authHeaders(),
body:fd
}
);

const data=
await res.json();

setUploadMessage(
data.message
);

}catch(e){
console.error(e);
setUploadMessage(
"Upload failed"
);
}
finally{
setUploadingResume(
false
);
}

};



/* ---------------- scroll ---------------- */

useEffect(()=>{
bottomRef.current?.
scrollIntoView({
behavior:"smooth"
});
},[messages]);



/* ---------------- LOGIN SCREEN ---------------- */

if(!loggedIn){

return(
<div className="min-h-screen flex items-center justify-center bg-gray-100">
<div className="bg-white p-6 rounded shadow w-[340px] space-y-4">

<h1 className="text-lg font-semibold text-center">
Northstar Login
</h1>

<input
value={username}
onChange={e=>
setUsername(
e.target.value
)
}
placeholder="User ID"
className="w-full border px-3 py-2 rounded"
/>

<input
type="password"
value={password}
onChange={e=>
setPassword(
e.target.value
)
}
className="w-full border px-3 py-2 rounded"
/>

{
loginError &&
<div className="text-sm text-red-500">
{loginError}
</div>
}

<button
onClick={login}
className="w-full bg-black text-white py-2 rounded"
>
Login
</button>

<div className="text-xs text-gray-500">
Demo password: demo123
</div>

</div>
</div>
);

}



/* ---------------- Sidebar ---------------- */

const Sidebar=()=>(
<aside className="w-60 border-r p-4 flex flex-col bg-gray-50">

<div className="font-semibold mb-6">
Northstar
</div>

{
Object.entries(
VIEW_CONFIG
).map(
([k,v])=>(
<button
key={k}
onClick={()=>
setView(k)
}
className={`w-full text-left px-3 py-2 rounded mb-2 ${
view===k
?"bg-gray-200"
:"hover:bg-gray-200"
}`}
>
{v.label}
</button>
))
}

<button
onClick={
openResumePicker
}
className="mt-4 border rounded px-3 py-2 text-left"
>
📄 Upload Resume
</button>

<input
type="file"
ref={fileInputRef}
accept=".pdf"
style={{
display:"none"
}}
onChange={
handleResumeUpload
}
/>

{
uploadingResume &&
<div className="text-xs mt-2">
Uploading...
</div>
}

{
uploadMessage &&
<div className="text-xs mt-2">
{uploadMessage}
</div>
}

<button
onClick={logout}
className="mt-auto border rounded px-3 py-2"
>
Logout
</button>

</aside>
);



/* ---------------- Chat ---------------- */

const ChatView=()=>(

<div className="flex flex-col h-full">

<div className="px-4 py-2 border-b flex justify-between text-sm">
<span>
{
connected
?"🟢 Online"
:"🔴 Offline"
}
</span>

{
speechSupported &&
<button
onClick={
toggleRecording
}
>
{
isRecording
?"⏹ Stop"
:"🎤 Mic"
}
</button>
}

</div>

<div className="flex-1 overflow-y-auto p-4 space-y-3">

{
messages.map(
(m,i)=>(
<div
key={i}
className={
m.sender==="user"
?"text-right":""
}
>
<div className="inline-block bg-gray-100 px-3 py-2 rounded">
{
m.sender==="user"
?m.text
:
<ReactMarkdown
remarkPlugins={[
remarkGfm
]}
rehypePlugins={[
rehypeHighlight
]}
>
{m.text}
</ReactMarkdown>
}
</div>
</div>
))
}

<div ref={bottomRef}/>

</div>

<div className="p-3 border-t flex gap-2">

<input
ref={inputRef}
value={input}
onChange={e=>
setInput(
e.target.value
)
}
className="flex-1 border px-3 py-2 rounded"
onKeyDown={e=>{
if(
e.key==="Enter"
){
sendMessage();
}
}}
/>

<button
onClick={sendMessage}
className="bg-black text-white px-4 rounded"
>
Send
</button>

</div>

</div>

);



/* ---------------- Content ---------------- */

const ContentView=()=>(

<div className="p-6 space-y-3">

<div className="text-lg font-semibold mb-2">
{VIEW_CONFIG[view]?.label}
</div>

{
loadingResources &&
<div>
Loading...
</div>
}

{
!loadingResources &&
resources.length===0 &&
<div className="text-sm text-gray-400">
No items found.
</div>
}

{
resources.map((r,i)=>{

const id=
r.id||
r._id||
r.resource_id||
i;

return(
<div
key={id}
className="border p-4 rounded group relative"
>

<a
href={
r.url||
r.link||
"#"
}
target="_blank"
rel="noreferrer"
className="font-medium text-blue-600"
>
{r.title||"Untitled"}
</a>

{
r.description &&
<div className="text-sm mt-1 text-gray-500">
{r.description}
</div>
}

<div className="absolute right-3 top-3 hidden group-hover:flex gap-2">

<button
onClick={()=>
archiveResource(id)
}
className="text-xs border px-2 py-1 rounded"
>
Archive
</button>

<button
onClick={()=>
deleteResource(id)
}
className="text-xs border px-2 py-1 rounded"
>
Delete
</button>

</div>

</div>
)

})
}

</div>

);



return(
<div className="h-screen flex">
<Sidebar/>
<div className="flex-1">
{
view==="chat"
?<ChatView/>
:<ContentView/>
}
</div>
</div>
);

}