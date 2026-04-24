import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

/* ---------------- VIEW CONFIG ---------------- */

const VIEW_CONFIG = {
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
const [loggedIn,setLoggedIn]=useState(false);

const [view,setView]=useState("chat");

const [messages,setMessages]=useState([]);
const [thinking,setThinking]=useState([]);
const [input,setInput]=useState("");
const [showThinking]=useState(true);
const [isTyping,setIsTyping]=useState(false);
const [connected,setConnected]=useState(false);

const [resources,setResources]=useState([]);
const [loadingResources,setLoadingResources]=useState(false);

/* ---------- Resume upload ---------- */

const [uploadingResume,setUploadingResume]=useState(false);
const [uploadMessage,setUploadMessage]=useState("");
const fileInputRef=useRef(null);

/* ---------- Voice ---------- */

const [speechSupported,setSpeechSupported]=useState(false);
const [isRecording,setIsRecording]=useState(false);

const recognitionRef=useRef(null);

/* ---------- refs ---------- */

const wsRef=useRef(null);
const bottomRef=useRef(null);
const inputRef=useRef(null);


/* ---------------- WEBSOCKET ---------------- */

useEffect(()=>{

if(!loggedIn || !username) return;

const ws=
new WebSocket(
`ws://localhost:5000/ws/${username}`
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
setThinking(prev=>[
...prev,
data.think
]);
}

if(data.message){

setMessages(prev=>[
...prev,
{
sender:"server",
text:data.message
}
]);

setIsTyping(false);

}

}catch(e){
console.error(
"WS parse error",
e
);
}

};

return()=>{
ws.close();
};

},[
loggedIn,
username
]);



/* ---------------- SPEECH ---------------- */

useEffect(()=>{

const SpeechRecognition=
window.SpeechRecognition||
window.webkitSpeechRecognition;

if(!SpeechRecognition){
setSpeechSupported(false);
return;
}

setSpeechSupported(true);

const recognition=
new SpeechRecognition();

recognition.continuous=false;
recognition.interimResults=false;
recognition.lang="en-US";

recognition.onstart=()=>{
setIsRecording(true);
};

recognition.onresult=(event)=>{

try{

let text="";

for(
let i=0;
i<event.results.length;
i++
){

if(
event.results[i].isFinal
){
text+=
event.results[i][0]
.transcript;
}

}

if(text.trim()){

setInput(prev=>
prev
? prev+" "+text.trim()
: text.trim()
);

}

}catch(e){
console.error(e);
}

};

recognition.onerror=(e)=>{
console.error(e);
setIsRecording(false);
};

recognition.onend=()=>{
setIsRecording(false);
};

recognitionRef.current=
recognition;

return()=>{
try{
recognition.stop();
}catch{}
};

},[]);



const toggleRecording=()=>{

if(
!recognitionRef.current
)return;

if(isRecording){
recognitionRef.current.stop();
}else{
try{
recognitionRef.current.start();
}catch(e){
console.error(e);
}
}

};



/* ------------ Resume Upload ------------ */

const openResumePicker=()=>{
if(fileInputRef.current){
fileInputRef.current.click();
}
};

const handleResumeUpload=
async(e)=>{

try{

const file=
e.target.files?.[0];

if(!file) return;

setUploadMessage("");

if(
file.type!=="application/pdf"
){
setUploadMessage(
"Only PDF files allowed"
);
return;
}

if(
file.size >
5*1024*1024
){
setUploadMessage(
"File must be under 5 MB"
);
return;
}

setUploadingResume(true);

const formData=
new FormData();

formData.append(
"file",
file
);

const res=
await fetch(
`http://localhost:5000/upload_resume/${username}`,
{
method:"POST",
body:formData
}
);

const data=
await res.json();

if(data.success){
setUploadMessage(
"Resume uploaded successfully"
);
}else{
setUploadMessage(
data.message||
"Upload failed"
);
}

}catch(e){

console.error(e);

setUploadMessage(
"Upload failed"
);

}
finally{
setUploadingResume(false);

if(fileInputRef.current){
fileInputRef.current.value="";
}
}

};



/* ---------------- SCROLL ---------------- */

useEffect(()=>{
bottomRef.current?.
scrollIntoView({
behavior:"smooth"
});
},[
messages,
isTyping
]);



/* ---------------- FOCUS ---------------- */

useEffect(()=>{

if(
!isRecording &&
document.activeElement
!==inputRef.current
){
inputRef.current?.focus();
}

},[
input,
isRecording
]);



/* ---------------- SEND ---------------- */

const sendMessage=()=>{

if(!input.trim())
return;

const ws=
wsRef.current;

if(
!ws ||
ws.readyState
!==WebSocket.OPEN
){
return;
}

setThinking([]);
setIsTyping(true);

ws.send(
JSON.stringify({
message:input
})
);

setMessages(prev=>[
...prev,
{
sender:"user",
text:input
}
]);

setInput("");

};



/* ---------------- FETCH ---------------- */

const fetchResources=
async()=>{

const apiType=
VIEW_CONFIG[view]?.apiType;

if(!apiType) return;

setLoadingResources(
true
);

try{

const res=
await fetch(
`http://localhost:5000/get_resource_by_type/${username}/${apiType}`,
{
method:"POST"
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
if(view!=="chat"){
fetchResources();
}
},[view]);


const archiveResource=
async(id)=>{

await fetch(
`http://localhost:5000/update_resource_status/${username}/${id}`,
{
method:"POST",
headers:{
"Content-Type":
"application/json"
},
body:
JSON.stringify({
status:"archived"
})
}
);

setResources(
prev=>
prev.filter(
r=>
(
r.id||
r._id||
r.resource_id
)!==id
)
);

};


const deleteResource=
async(id)=>{

await fetch(
`http://localhost:5000/delete_resource/${username}/${id}`,
{
method:"DELETE"
}
);

setResources(
prev=>
prev.filter(
r=>
(
r.id||
r._id||
r.resource_id
)!==id
)
);

};



/* ---------------- LOGIN ---------------- */

if(!loggedIn){

return(
<div className="min-h-screen flex items-center justify-center bg-gray-100">
<div className="bg-white p-6 rounded-lg shadow w-[320px] space-y-4">

<h1 className="text-lg font-semibold text-center">
Northstar
</h1>

<input
value={username}
onChange={e=>
setUsername(
e.target.value
)
}
placeholder="Enter your name"
className="w-full border px-3 py-2 rounded"
/>

<button
onClick={()=>
username.trim() &&
setLoggedIn(true)
}
className="w-full bg-black text-white py-2 rounded"
>
Continue
</button>

</div>
</div>
);

}



/* ---------------- SIDEBAR ---------------- */

const Sidebar=()=>(
<aside className="w-60 border-r p-4 flex flex-col bg-gray-50">

<div className="font-semibold mb-6">
Northstar
</div>

{
Object.entries(
VIEW_CONFIG
).map(
([key,cfg])=>(
<button
key={key}
onClick={()=>
setView(key)
}
className={`w-full text-left px-3 py-2 rounded mb-2 ${
view===key
? "bg-gray-200"
: "hover:bg-gray-200"
}`}
>
{cfg.label}
</button>
))
}

<button
onClick={openResumePicker}
className="w-full text-left px-3 py-2 rounded mt-4 border hover:bg-gray-100"
>
📄 Upload Resume
</button>

<input
ref={fileInputRef}
type="file"
accept="application/pdf,.pdf"
style={{display:"none"}}
onChange={handleResumeUpload}
/>

{
uploadingResume &&
<div className="text-xs mt-2 text-gray-500">
Uploading...
</div>
}

{
uploadMessage &&
<div className="text-xs mt-2">
{uploadMessage}
</div>
}

</aside>
);



/* ---------------- CHAT ---------------- */

const ChatView=()=>(
<div className="flex flex-col h-full">

<div className="px-4 py-2 border-b text-sm flex justify-between">

<span>
{
connected
?"🟢 Online"
:"🔴 Offline"
}
</span>

{
speechSupported &&
<span className="text-xs text-gray-500">
{
isRecording
?"🎙 Recording..."
:"Mic Ready"
}
</span>
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

{
showThinking &&
thinking.length>0 &&
<div className="text-xs text-gray-500 border-t pt-2">
{
thinking.map(
(t,i)=>(
<div key={i}>
• {t}
</div>
))
}
</div>
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
placeholder="Type or use mic..."
className="flex-1 border px-3 py-2 rounded"
onKeyDown={e=>{
if(
e.key==="Enter"
){
e.preventDefault();
sendMessage();
}
}}
/>

{
speechSupported &&
<button
onClick={
toggleRecording
}
className={`px-4 rounded border ${
isRecording
?"bg-red-500 text-white"
:"bg-white"
}`}
>
{
isRecording
?"⏹ Stop"
:"🎤 Mic"
}
</button>
}

<button
onClick={sendMessage}
className="bg-black text-white px-4 rounded"
>
Send
</button>

</div>

</div>
);



/* ---------------- CONTENT ---------------- */

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

const url=
r.url||
r.link||
"#";

return(
<div
key={id}
className="border p-4 rounded relative hover:bg-gray-50 group"
>

<a
href={url}
target="_blank"
rel="noopener noreferrer"
className="font-medium text-blue-600 hover:underline block"
>
{r.title||"Untitled"}
</a>

{
r.channel &&
<div className="text-xs text-gray-500 mt-1">
{r.channel}
</div>
}

{
r.description &&
<div className="text-sm text-gray-500 mt-1">
{r.description}
</div>
}

{
r.tags?.length>0 &&
<div className="flex gap-2 mt-2 flex-wrap">
{
r.tags.map(
(tag,idx)=>(
<span
key={idx}
className="text-xs px-2 py-1 bg-gray-200 rounded"
>
{tag}
</span>
))
}
</div>
}

<div className="absolute right-3 top-3 hidden group-hover:flex gap-2">

<button
onClick={()=>
archiveResource(id)
}
className="text-xs px-2 py-1 border rounded"
>
Archive
</button>

<button
onClick={()=>
deleteResource(id)
}
className="text-xs px-2 py-1 border rounded text-red-600"
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



/* ---------------- APP ---------------- */

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