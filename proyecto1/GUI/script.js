const CFG_KEY = 'edificio_iot_cfg';
let mqttClient = null, lastTelemetry = 0, historyTimer = null;
const pendingHistory = new Map(), pendingCommands = new Map();
function set(id,value){ const el=document.getElementById(id); if(el) el.textContent=value; }
function loadConfig(){
  let c;
  try { c=JSON.parse(localStorage.getItem(CFG_KEY)) || {}; } catch { c={}; }
  if(typeof c !== 'object' || Array.isArray(c)) c={};
  if(!c.prefix || ['ARQUI1/edificio','ARQUI1_DANIEL/edificio'].includes(c.prefix))
    c.prefix='ARQUIG9:v/edificio';
  return c;
}
function toggleConfig(){ document.getElementById('configPanel').classList.toggle('open'); }
function fillConfigForm(c){
  for(const [id,value] of Object.entries({'url':c.mqttUrl||'', 'user':c.mqttUser||'', 'pass':c.mqttPass||'', 'prefix':c.prefix||'ARQUIG9:v/edificio'}))
    document.getElementById('cfg-mqtt-'+id).value=value;
}
function saveConfig(){
  const c={};
  for(const [field,id] of Object.entries({mqttUrl:'url',mqttUser:'user',mqttPass:'pass',prefix:'prefix'}))
    c[field]=document.getElementById('cfg-mqtt-'+id).value.trim();
  c.prefix=c.prefix.replace(/\/+$/,'') || 'ARQUIG9:v/edificio';
  if(!/^wss?:\/\//.test(c.mqttUrl) || /[+#]/.test(c.prefix)){
    set('commandStatus','Usá una URL ws:// o wss:// y un prefijo sin comodines.'); return;
  }

  const stored={...c}; delete stored.mqttPass;
  localStorage.setItem(CFG_KEY,JSON.stringify(stored));
  toggleConfig(); connectMqtt(c);
}
function makeChart(id,label,color){
  return new Chart(document.getElementById(id),{type:'line',data:{labels:[],datasets:[{label,data:[],borderColor:color,tension:.25,pointRadius:0}]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,spanGaps:false,plugins:{legend:{labels:{color:'#E7F1F8'}}},scales:{x:{ticks:{color:'#7FA1BC',maxTicksLimit:6}},y:{ticks:{color:'#7FA1BC'}}}}});
}
const charts={temp:makeChart('chartTemp','Temperatura °C','#F87171'),hum:makeChart('chartHum','Humedad %','#4FC3E0'),
 gas:makeChart('chartGas','Gas ADC','#FBBF24'),dist:makeChart('chartDist','Distancia cm','#4ADE80'),
 luz:makeChart('chartLuz','Luz relativa %','#C084FC'),arm:makeChart('chartArm','Promedio ARM64','#4FC3E0')};
const points=Object.fromEntries(Object.keys(charts).map(k=>[k,new Map()]));
function numeric(v){ return typeof v==='number' && Number.isFinite(v) ? v : null; }
function pushPoint(key,value,ts){
  const t=Date.parse(ts); if(!Number.isFinite(t)) return;
  points[key].set(t,numeric(value));
  const ordered=[...points[key]].sort((a,b)=>a[0]-b[0]).slice(-200);
  points[key]=new Map(ordered);
  const chart=charts[key]; chart.data.labels=ordered.map(([x])=>new Date(x).toLocaleTimeString());
  chart.data.datasets[0].data=ordered.map(([,y])=>y); chart.update('none');
}
function enableControls(on){ document.querySelectorAll('.controls button').forEach(b=>b.disabled=!on); }
function setGlobalStatus(state){
  const valid=['NORMAL','ADVERTENCIA','EMERGENCIA'];
  const s=valid.includes(state)?state:'ADVERTENCIA';
  const badge=document.getElementById('globalStatus');badge.textContent=s;badge.className='status-badge '+s;
}
function disconnected(text){
  enableControls(false); set('connText',text); document.getElementById('connDot').classList.remove('on');
  setGlobalStatus('ADVERTENCIA'); set('globalStatus','SIN CONEXIÓN');
}
function connectMqtt(cfg){
  if(mqttClient) mqttClient.end(true);
  clearInterval(historyTimer); pendingHistory.clear(); pendingCommands.clear();lastTelemetry=0;
  disconnected('Conectando MQTT…');
  const client=mqtt.connect(cfg.mqttUrl,{username:cfg.mqttUser||undefined,password:cfg.mqttPass||undefined,reconnectPeriod:4000});
  mqttClient=client;
  const prefix=cfg.prefix || 'ARQUIG9:v/edificio';
  client.on('connect',()=>{
    if(client!==mqttClient)return;
    set('connText','Broker conectado; esperando Raspberry');
    const paths=['sensores/+','actuadores/+','estado/global','arm64/resultados','control/respuesta','historial/respuesta/+','conexion','diagnostico'];
    client.subscribe(paths.map(p=>prefix+'/'+p),{qos:1},err=>{if(!err) refreshHistorial();});
  });
  client.on('message',(topic,message)=>{
    if(client!==mqttClient || !topic.startsWith(prefix+'/'))return;
    try{handleMessage(topic.slice(prefix.length+1),JSON.parse(message.toString()));}catch(e){console.warn('Mensaje ignorado',e.message);}
  });
  client.on('close',()=>{if(client===mqttClient)disconnected('MQTT desconectado');});
  client.on('error',()=>{if(client===mqttClient)disconnected('Error MQTT; revisá la configuración');});
  client._prefix=prefix;
  historyTimer=setInterval(refreshHistorial,15000);
}
const sensorMap={temperatura:['temp','r-temp','z-temp',' °C'],humedad:['hum','r-hum','z-hum',' %'],
 gas:['gas','r-gas','z-gas',' ADC'],distancia:['dist','r-dist','z-dist',' cm'],luz:['luz','r-luz','z-luz',' %']};
function handleMessage(topic,val){
  if(!val || typeof val!=='object')return;
  if(topic==='estado/global'){
    lastTelemetry=Date.now();setGlobalStatus(val.estado); enableControls(true);
    set('connText','Raspberry conectada');document.getElementById('connDot').classList.add('on');
  }else if(topic.startsWith('sensores/')){
    const m=sensorMap[topic.split('/')[1]];if(!m)return;
    const n=numeric(val.valor), text=n===null?'SIN DATOS':n+m[3]+(val.reutilizado?' (anterior)':'');
    set(m[1],text);set(m[2],text);pushPoint(m[0],n,val.timestamp);
  }else if(topic.startsWith('actuadores/')){
    const key=topic.split('/')[1], ids={puerta:'z-puerta',luces:'z-luces',ventilador:'z-vent',alarma:'z-alarma'};
    if(ids[key])set(ids[key],typeof val.estado==='string'?val.estado:'SIN DATOS');
    if(key==='luces'){
      set('z-modo',val.modo || 'SIN DATOS');
      set('zonasLuces',Object.entries(val.zonas||{}).map(([k,v])=>k+': '+v).join(' · '));
    }
  }else if(topic==='arm64/resultados'){
    showArm(val);pushPoint('arm',val.promedio,val.timestamp);
  }else if(topic==='control/respuesta'){
    if(pendingCommands.has(val.id)){
      pendingCommands.delete(val.id);set('commandStatus',(val.aceptado?'Confirmado: ':'Rechazado: ')+val.mensaje);
      refreshHistorial();
    }
  }else if(topic.startsWith('historial/respuesta/')){
    const request=pendingHistory.get(val.id);if(!request)return;
    pendingHistory.delete(val.id);
    if(val.error){set('historyStatus','Historial: '+val.error);return;}
    if(val.coleccion!==request.collection || !Array.isArray(val.documentos))return;
    renderHistory(val.coleccion,val.documentos);set('historyStatus','Historial consultado en Atlas: '+new Date().toLocaleTimeString());
  }else if(topic==='conexion' && val.conectado===false){lastTelemetry=0;disconnected('Raspberry desconectada');}
  else if(topic==='diagnostico'){
    const errores=Object.entries(val.errores||{}).map(([k,v])=>k+': '+v).join(' | ');
    set('diagnostico','HARDWARE REAL — '+(errores||'Sin errores de sensores reportados'));
  }
}
function showArm(d){
  set('r-arm-avg',d.promedio??'--');
  set('armDetails',`ARM64: máximo ${d.maximo??'--'} · mínimo ${d.minimo??'--'} · promedio ${d.promedio??'--'} · cantidad ${d.cantidad??'--'}`);
}
function uniqueId(){return 'web_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,10);}
function sendCmd(comando,accion){
  if(!mqttClient?.connected || !lastTelemetry || Date.now()-lastTelemetry>20000){set('commandStatus','Esperá la conexión de la Raspberry.');return;}
  const id=uniqueId(), ts=new Date().toISOString();pendingCommands.set(id,Date.now());
  mqttClient.publish(mqttClient._prefix+'/control/remoto',JSON.stringify({id,comando,accion,ts}),{qos:1,retain:false});
  set('commandStatus','Esperando confirmación: '+comando+' '+accion);
}
function refreshHistorial(){
  if(!mqttClient?.connected)return;
  const now=Date.now();
  for(const [id,r] of pendingHistory)if(now-r.time>12000){pendingHistory.delete(id);set('historyStatus','Historial sin respuesta; revisá Python y Atlas.');}
  for(const collection of ['sensor_readings','events','commands','arm64_results']){
    if([...pendingHistory.values()].some(r=>r.collection===collection))continue;
    const id=uniqueId();pendingHistory.set(id,{collection,time:now});
    mqttClient.publish(mqttClient._prefix+'/historial/solicitud',JSON.stringify({id,coleccion:collection,limite:collection==='sensor_readings'?100:40}),{retain:false});
  }
}
function table(id,docs,row){
  const body=document.querySelector('#'+id+' tbody');body.replaceChildren();
  for(const values of docs.length?docs.map(row):[['—','Sin datos']]){
    const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.textContent=String(value);tr.appendChild(td);}body.appendChild(tr);
  }
}
function fmtTs(ts){const n=Date.parse(ts);return Number.isFinite(n)?new Date(n).toLocaleString():'—';}
function renderHistory(collection,docs){
  if(collection==='sensor_readings'){
    for(const d of docs)for(const [key,m] of Object.entries(sensorMap))pushPoint(m[0],d[key],d.timestamp);
  }else if(collection==='events')table('tblEvents',docs,d=>[fmtTs(d.timestamp),d.mensaje||d.tipo||'—']);
  else if(collection==='commands')table('tblCommands',docs,d=>[fmtTs(d.timestamp),`${d.comando||d.action||'?'} ${d.accion||d.value||''} · ${d.aceptado?'ejecutado':'rechazado'} · ${d.mensaje||''}`]);
  else if(collection==='arm64_results'){
    table('tblArm',docs,d=>[fmtTs(d.timestamp),`${d.maximo} / ${d.minimo} / ${d.promedio} / ${d.cantidad}`]);
    for(const d of docs)pushPoint('arm',d.promedio,d.timestamp);
    if(docs.length)showArm(docs[0]);
  }
}
window.addEventListener('DOMContentLoaded',()=>{
  enableControls(false);const c=loadConfig();delete c.mongoKey;delete c.mqttPass;localStorage.setItem(CFG_KEY,JSON.stringify(c));fillConfigForm(c);
  if(c.mqttUrl)connectMqtt(c);else toggleConfig();
  setInterval(()=>{
    if(lastTelemetry && Date.now()-lastTelemetry>20000){lastTelemetry=0;disconnected('Sin lecturas recientes de Raspberry');}
    for(const [id,t] of pendingCommands)if(Date.now()-t>10000){pendingCommands.delete(id);set('commandStatus','Sin confirmación: no se puede asegurar que el comando se ejecutó.');}
  },1000);
});
