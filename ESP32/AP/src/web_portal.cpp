#include "web_portal.h"
#include "http_client.h"
#include "config.h"
#include <ArduinoJson.h>

// ─────────────────────────────────────────────────────────────────────────────
// HTML portal — mobile-friendly, ~3 KB, almacenado en flash (PROGMEM)
// ─────────────────────────────────────────────────────────────────────────────
const char WebPortal::_HTML[] PROGMEM = R"PORTAL(
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exalink Gateway</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#eef2f7;padding:16px;max-width:520px;margin:0 auto}
h1{color:#1a56db;text-align:center;font-size:1.35em;margin:12px 0 18px}
.card{background:#fff;border-radius:12px;padding:16px;
      margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.1)}
.card h2{font-size:.95em;color:#6b7280;margin-bottom:12px;
         padding-bottom:8px;border-bottom:1px solid #f0f0f0;
         text-transform:uppercase;letter-spacing:.05em}
.row{display:flex;justify-content:space-between;align-items:center;
     font-size:.9em;padding:5px 0;border-bottom:1px solid #f9f9f9}
.row:last-child{border-bottom:none}
.lbl{color:#9ca3af;font-size:.8em}
.ok{color:#16a34a;font-weight:600}
.err{color:#dc2626;font-weight:600}
label{display:block;font-size:.82em;color:#6b7280;margin-top:12px;margin-bottom:4px}
input,select{width:100%;padding:10px;border:1px solid #d1d5db;
             border-radius:8px;font-size:.95em;background:#fafafa}
input:focus,select:focus{outline:none;border-color:#1a56db;background:#fff}
button{display:block;width:100%;padding:12px;border:none;
       border-radius:8px;font-size:1em;font-weight:600;
       cursor:pointer;margin-top:12px;transition:opacity .2s}
button:active{opacity:.8}
.btn-p{background:#1a56db;color:#fff}
.btn-s{background:#6b7280;color:#fff}
.btn-d{background:#dc2626;color:#fff}
#scan-wrap{margin-top:10px}
</style>
</head>
<body>
<h1>&#128225; Exalink Gateway</h1>

<div class="card">
  <h2>Estado</h2>
  <div id="status">Cargando&hellip;</div>
</div>

<div class="card">
  <h2>Red WiFi</h2>
  <button class="btn-s" onclick="scan()">&#128268; Escanear redes</button>
  <div id="scan-wrap"></div>
  <label>SSID</label>
  <input type="text" id="ssid" placeholder="Nombre de red">
  <label>Contrase&ntilde;a</label>
  <div style="position:relative">
    <input type="password" id="pass" placeholder="Contrase&ntilde;a WiFi" style="padding-right:42px">
    <span id="eye" onclick="togglePass()" title="Mostrar/ocultar"
      style="position:absolute;right:10px;top:50%;transform:translateY(-50%);
             cursor:pointer;font-size:1.2em;user-select:none;line-height:1">&#128065;</span>
  </div>
  <p style="font-size:.78em;color:#9ca3af;margin:8px 0 4px">
    Si la nueva red no responde, el gateway vuelve a la anterior autom&aacute;ticamente.</p>
  <button class="btn-p" onclick="applyWifi()">&#128268;&nbsp;Aplicar WiFi</button>
</div>

<div class="card">
  <h2>Gateway</h2>
  <label>ID Interno <span style="color:#9ca3af;font-size:.85em">(solo lectura)</span></label>
  <input type="text" id="gw_id" readonly
         style="background:#f3f4f6;color:#6b7280;cursor:default;font-family:monospace;font-size:.9em"
         placeholder="Generando...">
  <label>URL Servidor LoRaWAN</label>
  <input type="url" id="server" placeholder="https://10.1.1.100:6666">
  <div id="srv-st" style="margin:8px 0 2px;font-size:.82em">No verificado</div>
  <div style="display:flex;gap:8px;margin-top:0">
    <button class="btn-s" id="btn-tst" onclick="testSrv()" style="margin-top:0;flex:1">&#9654;&nbsp;Test Conexi&oacute;n</button>
    <button class="btn-s" id="btn-fsync" onclick="forceSync()" style="margin-top:0;flex:1">&#8635;&nbsp;Sync Ahora</button>
  </div>
  <label>Frecuencia LoRa</label>
  <select id="freq" onchange="onFreqChg()">
    <option value="915.0">915.0 MHz &mdash; AU915/AR (default)</option>
    <option value="915.2">915.2 MHz &mdash; AU915 ch1</option>
    <option value="915.4">915.4 MHz &mdash; AU915 ch2</option>
    <option value="915.6">915.6 MHz &mdash; AU915 ch3</option>
    <option value="915.8">915.8 MHz &mdash; AU915 ch4</option>
    <option value="916.0">916.0 MHz &mdash; AU915 ch5</option>
    <option value="916.2">916.2 MHz &mdash; AU915 ch6</option>
    <option value="916.4">916.4 MHz &mdash; AU915 ch7</option>
    <option value="916.6">916.6 MHz &mdash; AU915 ch8</option>
    <option value="923.2">923.2 MHz &mdash; AS923</option>
    <option value="868.1">868.1 MHz &mdash; EU868 ch1</option>
    <option value="868.3">868.3 MHz &mdash; EU868 ch2</option>
    <option value="868.5">868.5 MHz &mdash; EU868 ch3</option>
    <option value="433.175">433.175 MHz &mdash; AS433</option>
    <option value="custom">Personalizada&hellip;</option>
  </select>
  <input type="number" id="freq_c" step="0.1" min="433" max="928"
         placeholder="Frecuencia en MHz" style="display:none;margin-top:6px">
  <label>Contrase&ntilde;a LoRaWAN (Bearer token)</label>
  <div style="position:relative">
    <input type="password" id="lorawan_pass" placeholder="abc1234"
           autocomplete="new-password" style="padding-right:42px">
    <span onclick="toggleLPass()" title="Mostrar/ocultar"
      style="position:absolute;right:10px;top:50%;transform:translateY(-50%);
             cursor:pointer;font-size:1.2em;user-select:none;line-height:1">&#128065;</span>
  </div>
  <label>Puerto HTTPS Listener</label>
  <input type="number" id="listen_port" min="1" max="65535" placeholder="6666">
  <label>Intervalo de sync con servidor (minutos)</label>
  <input type="number" id="sync_interval" min="1" max="1440" placeholder="1">
  <button class="btn-p" onclick="save()">&#10003;&nbsp;Guardar y Reiniciar</button>
</div>

<div class="card">
  <h2>Restablecer</h2>
  <p style="font-size:.82em;color:#9ca3af;margin-bottom:4px">
    Borra toda la configuraci&oacute;n guardada y vuelve a valores de f&aacute;brica.</p>
  <button class="btn-d" onclick="rst()">&#9888;&nbsp;Resetear Configuraci&oacute;n</button>
</div>

<script>
var gwData={};
function srvBadge(d){
  if(!d.server_tested)return '<span style="color:#9ca3af">No verificado</span>';
  if(!d.server_ok)return '<span class="err">&#10007; Error de conexi&oacute;n</span>';
  var lat=(d.sync_latency_ms>=0)?' <span style="color:#9ca3af;font-size:.85em">('+d.sync_latency_ms+'ms)</span>':'';
  return '<span class="ok">&#10003; Conectado</span>'+lat;
}
async function testSrv(){
  var btn=document.getElementById('btn-tst');
  var st=document.getElementById('srv-st');
  btn.disabled=true;
  st.innerHTML='<span style="color:#9ca3af">Probando&hellip;</span>';
  try{
    var url=document.getElementById('server').value.trim();
    var r=await fetch('/test-server?url='+encodeURIComponent(url));
    var d=await r.json();
    if(d.ok){
      st.innerHTML='<span class="ok">&#10003; Conectado</span>&nbsp;<span style="color:#9ca3af;font-size:.85em">'+esc(d.url)+'</span>';
    }else{
      st.innerHTML='<span class="err">&#10007; Error</span>&nbsp;<span style="color:#9ca3af;font-size:.85em">'+(d.msg?esc(d.msg):esc(d.url))+'</span>';
    }
  }catch(e){
    st.innerHTML='<span class="err">&#10007; Error al conectar con el gateway</span>';
  }
  btn.disabled=false;
  fetchStatus();
}
async function fetchStatus(){
  try{
    var d=await(await fetch('/status')).json();
    gwData=d;
    var wf=d.wifi_ok
      ?'<span class="ok">'+d.wifi_ssid+'&nbsp;&mdash;&nbsp;'+d.ip+'</span>'
      :'<span class="err">Sin conexi&oacute;n</span>';
    document.getElementById('status').innerHTML=
      '<div class="row"><span class="lbl">Gateway ID</span><strong>'+d.gw_id+'</strong></div>'+
      '<div class="row"><span class="lbl">WiFi</span>'+wf+'</div>'+
      '<div class="row"><span class="lbl">LoRa</span><span class="ok">'+d.freq+' MHz</span></div>'+
      '<div class="row"><span class="lbl">Paquetes RX</span><strong>'+d.pkts+'</strong></div>'+
      '<div class="row"><span class="lbl">Servidor</span><span style="font-size:.8em;word-break:break-all">'+d.server+'</span></div>'+
      '<div class="row"><span class="lbl">HTTPS Listener</span><span class="ok">Puerto '+d.listen_port+'</span></div>'+
      '<div class="row"><span class="lbl">LoRaWAN Server</span>'+srvBadge(d)+'</div>';
    document.getElementById('gw_id').value=d.gw_id;
    document.getElementById('server').value=d.server;
    var sSt=document.getElementById('srv-st');
    if(sSt)sSt.innerHTML=srvBadge(d)+'&nbsp;<span style="color:#9ca3af;font-size:.9em">'+
      (d.server_tested?'':'(no verificado)')+'</span>';
    var freqList=['915.0','915.2','915.4','915.6','915.8','916.0','916.2','916.4','916.6',
                  '923.2','868.1','868.3','868.5','433.2'];
    var fStr=(Math.round(d.freq*10)/10).toFixed(1);
    var fSel=document.getElementById('freq');
    var fCust=document.getElementById('freq_c');
    if(freqList.indexOf(fStr)>=0){fSel.value=fStr;fCust.style.display='none';}
    else{fSel.value='custom';fCust.value=d.freq;fCust.style.display='block';}
    document.getElementById('lorawan_pass').value=d.lorawan_pass||'';
    document.getElementById('listen_port').value=d.listen_port||'6666';
    document.getElementById('sync_interval').value=d.sync_interval||'1';
    if(d.wifi_ssid)document.getElementById('ssid').placeholder='Actual: '+d.wifi_ssid;
    var dayAttempted=d.day_pkts_attempted||0;
    var daySent=d.day_pkts_sent||0;
    var loss=dayAttempted>0?((1-daySent/dayAttempted)*100).toFixed(1):'0.0';
    var dailyStr=dayAttempted>0
      ?(daySent+'/'+dayAttempted+' paq &mdash; <span style="color:'+(loss>10?'#dc2626':'#16a34a')+'">'+loss+'% p&eacute;rdida</span>')
      :'Sin datos hoy';
    document.getElementById('status').innerHTML+=
      '<div class="row"><span class="lbl">Hoy (paquetes)</span><span>'+dailyStr+'</span></div>';
  }catch(e){
    document.getElementById('status').innerHTML='<span class="err">Error al conectar</span>';
  }
}
function onFreqChg(){
  var v=document.getElementById('freq').value;
  document.getElementById('freq_c').style.display=(v==='custom')?'block':'none';
}
function getFreq(){
  var v=document.getElementById('freq').value;
  if(v==='custom')return parseFloat(document.getElementById('freq_c').value)||915.0;
  return parseFloat(v);
}
function togglePass(){
  var p=document.getElementById('pass');
  p.type=(p.type==='password')?'text':'password';
}
function toggleLPass(){
  var p=document.getElementById('lorawan_pass');
  p.type=(p.type==='password')?'text':'password';
}
async function applyWifi(){
  var s=document.getElementById('ssid').value.trim();
  if(!s){alert('Ingresa un SSID.');return;}
  if(!confirm('Aplicar WiFi: "'+s+'"\n\nSi falla la conexión el gateway volverá automáticamente a la red anterior.'))return;
  try{
    var r=await fetch('/wifi-apply',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ssid:s,pass:document.getElementById('pass').value})});
    var d=await r.json();
    alert(d.ok
      ?'Aplicando… El gateway se reiniciará y probará la nueva red.\nSi falla, volverá a la anterior solo.'
      :'Error: '+(d.msg||'Desconocido'));
  }catch(e){alert('Error de conexión.');}
}
async function scan(){
  var el=document.getElementById('scan-wrap');
  el.innerHTML='<p style="font-size:.85em;color:#9ca3af;margin-top:8px">Escaneando&hellip; (~5 s)</p>';
  try{
    var nets=await(await fetch('/scan')).json();
    if(!nets.length){el.innerHTML='<p style="color:#9ca3af;font-size:.85em;margin-top:8px">Sin redes.</p>';return;}
    var h='<select style="margin-top:8px" onchange="document.getElementById(\'ssid\').value=this.value"><option value="">-- Seleccionar --</option>';
    nets.forEach(function(n){h+='<option value="'+esc(n.ssid)+'">'+esc(n.ssid)+' ('+n.rssi+' dBm'+(n.enc?' &#128274;':'')+')';});
    el.innerHTML=h+'</select>';
  }catch(e){el.innerHTML='<p style="color:#dc2626;font-size:.85em;margin-top:8px">Error al escanear.</p>';}
}
async function forceSync(){
  var btn=document.getElementById('btn-fsync');
  btn.disabled=true;
  try{
    var r=await fetch('/force-sync',{method:'POST'});
    var d=await r.json();
    if(!d.ok)alert('Error al sincronizar: '+(d.msg||'Desconocido'));
  }catch(e){alert('Error de conexión.');}
  btn.disabled=false;
  setTimeout(fetchStatus,2500);
}
async function save(){
  var body={server:document.getElementById('server').value.trim(),
            freq:getFreq(),
            lorawan_pass:document.getElementById('lorawan_pass').value,
            listen_port:parseInt(document.getElementById('listen_port').value)||6666,
            sync_interval:parseInt(document.getElementById('sync_interval').value)||1};
  try{
    var r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    alert(d.ok?'Configuración guardada.\nReiniciando en 3 s…':'Error: '+d.msg);
  }catch(e){alert('Error de conexión.');}
}
async function rst(){
  if(!confirm('Resetear toda la configuración y reiniciar?'))return;
  try{await fetch('/reset');alert('Reseteado. Reiniciando…');}catch(e){}
}
function esc(s){var d=document.createElement('div');d.innerText=s;return d.innerHTML;}
fetchStatus();
setInterval(fetchStatus,10000);
</script>
</body>
</html>
)PORTAL";

// ─────────────────────────────────────────────────────────────────────────────
// WebPortal implementation
// ─────────────────────────────────────────────────────────────────────────────

WebPortal::WebPortal(ConfigManager& cfgMgr,
                     GatewayConfig& gwCfg,
                     LoRaManager&   lora)
    : _server(WEB_SERVER_PORT)
    , _cfgMgr(cfgMgr)
    , _gwCfg(gwCfg)
    , _lora(lora)
    , _restart(false)
    , _serverOk(false)
    , _serverTested(false)
    , _lastSyncLatencyMs(-1)
    , _forceSyncPending(false)
    , _dayPktsAttempted(0)
    , _dayPktsSent(0)
{}

void WebPortal::begin() {
    _server.on("/",            HTTP_GET,  [this]() { _handleRoot();        });
    _server.on("/status",      HTTP_GET,  [this]() { _handleStatus();      });
    _server.on("/scan",        HTTP_GET,  [this]() { _handleScan();        });
    _server.on("/save",        HTTP_POST, [this]() { _handleSave();        });
    _server.on("/reset",       HTTP_GET,  [this]() { _handleReset();       });
    _server.on("/test-server", HTTP_GET,  [this]() { _handleTestServer();  });
    _server.on("/wifi-apply",  HTTP_POST, [this]() { _handleWifiApply();   });
    _server.on("/force-sync",  HTTP_POST, [this]() { _handleForceSync();   });
    _server.onNotFound(                   [this]() { _handleNotFound();    });

    _server.begin();
    Serial.printf("[Web] Servidor HTTP en puerto %d\n", WEB_SERVER_PORT);
}

void WebPortal::handle() {
    _server.handleClient();
}

bool WebPortal::shouldRestart() const {
    return _restart;
}

void WebPortal::_handleRoot() {
    _server.send_P(200, "text/html", _HTML);
}

void WebPortal::_handleStatus() {
    bool staOK = (WiFi.status() == WL_CONNECTED);

    StaticJsonDocument<768> doc;
    doc["gw_id"]              = _gwCfg.gatewayId;
    doc["gw_name"]            = _gwCfg.gatewayName;
    doc["wifi_ok"]            = staOK;
    doc["wifi_ssid"]          = _gwCfg.wifiSsid;
    doc["ip"]                 = staOK ? WiFi.localIP().toString()
                                      : WiFi.softAPIP().toString();
    doc["freq"]               = _lora.getFreq();
    doc["pkts"]               = _lora.getPacketCount();
    doc["server"]             = _gwCfg.serverUrl;
    doc["lorawan_pass"]       = _gwCfg.lorawanPass;
    doc["listen_port"]        = _gwCfg.listenPort;
    doc["sync_interval"]      = _gwCfg.syncIntervalMin;
    doc["server_ok"]          = _serverOk;
    doc["server_tested"]      = _serverTested;
    doc["sync_latency_ms"]    = _lastSyncLatencyMs;
    doc["day_pkts_attempted"] = _dayPktsAttempted;
    doc["day_pkts_sent"]      = _dayPktsSent;

    String out;
    serializeJson(doc, out);
    _server.send(200, "application/json", out);
}

void WebPortal::setServerOk(bool ok, int32_t latencyMs) {
    _serverOk          = ok;
    _serverTested      = true;
    _lastSyncLatencyMs = ok ? latencyMs : -1;
}

bool WebPortal::isServerOk()     const { return _serverOk;     }
bool WebPortal::isServerTested() const { return _serverTested; }

void WebPortal::incDailyPkt(bool ok) {
    _dayPktsAttempted++;
    if (ok) _dayPktsSent++;
}

void WebPortal::resetDailyStats() {
    _dayPktsAttempted = 0;
    _dayPktsSent      = 0;
}

bool WebPortal::shouldForceSync() const { return _forceSyncPending; }
void WebPortal::clearForceSync()        { _forceSyncPending = false; }

void WebPortal::_handleForceSync() {
    if (WiFi.status() != WL_CONNECTED) {
        _server.send(503, "application/json",
                     "{\"ok\":false,\"msg\":\"Sin WiFi\"}");
        return;
    }
    _forceSyncPending = true;
    _server.send(200, "application/json", "{\"ok\":true}");
    Serial.println("[Web] Sync forzado solicitado.");
}

void WebPortal::_handleTestServer() {
    if (WiFi.status() != WL_CONNECTED) {
        _server.send(503, "application/json",
                     "{\"ok\":false,\"msg\":\"Sin WiFi\"}");
        return;
    }
    // Usar la URL del parámetro si la envía el cliente (para probar sin guardar)
    String testUrl = _gwCfg.serverUrl;
    if (_server.hasArg("url")) {
        String u = _server.arg("url");
        if (!u.isEmpty()) testUrl = u;
    }
    if (testUrl.isEmpty()) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"Sin URL configurada\"}");
        return;
    }

    LoRaPacket testPkt;
    testPkt.payloadHex = "4558414C494E4B54455354";   // "EXALINKTEST"
    testPkt.payloadB64 = "RVhBTElOS1RFU1Q=";
    testPkt.rssi       = -42;
    testPkt.snr        = 9.5f;
    testPkt.timestamp  = millis() / 1000;
    testPkt.isLoRaWAN  = false;
    testPkt.mtype      = 0;
    testPkt.devAddr    = 0;
    testPkt.fcnt       = 0;

    _serverTested = true;
    _serverOk = httpPostLoRaPacket(
        testUrl,
        _gwCfg.gatewayId,
        _gwCfg.lorawanPass,
        testPkt,
        _gwCfg.loraFreq,
        LORA_SF_DEFAULT,
        LORA_BW_DEFAULT
    );
    Serial.printf("[Web] Test servidor %s: %s\n", testUrl.c_str(), _serverOk ? "OK" : "FAIL");

    StaticJsonDocument<256> resp;
    resp["ok"]  = _serverOk;
    resp["url"] = testUrl + SERVER_ENDPOINT;
    String out;
    serializeJson(resp, out);
    _server.send(_serverOk ? 200 : 502, "application/json", out);
}

void WebPortal::_handleScan() {
    Serial.println("[Web] Escaneo WiFi solicitado...");

    int n = WiFi.scanNetworks();    // sincrónico (~3-5 s)

    String json = "[";
    bool first = true;
    for (int i = 0; i < n && i < 20; i++) {
        String ssid = WiFi.SSID(i);
        if (ssid.isEmpty()) continue;   // ignorar redes ocultas / sin nombre
        ssid.replace("\\", "\\\\");
        ssid.replace("\"", "\\\"");
        if (!first) json += ",";
        first = false;
        json += "{\"ssid\":\"" + ssid + "\","
                "\"rssi\":"  + String(WiFi.RSSI(i)) + ","
                "\"enc\":"   + (WiFi.encryptionType(i) != WIFI_AUTH_OPEN
                                ? "true" : "false") + "}";
    }
    json += "]";

    WiFi.scanDelete();
    _server.send(200, "application/json", json);
}

void WebPortal::_handleSave() {
    if (!_server.hasArg("plain")) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"Sin cuerpo JSON\"}");
        return;
    }

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, _server.arg("plain"));
    if (err) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"JSON invalido\"}");
        return;
    }

    _gwCfg.serverUrl   = doc["server"].as<String>();
    _gwCfg.lorawanPass = doc["lorawan_pass"].as<String>();
    if (_gwCfg.lorawanPass.isEmpty()) _gwCfg.lorawanPass = LORAWAN_DEFAULT_PASS;
    _gwCfg.listenPort      = doc["listen_port"]   | LORAWAN_LISTEN_PORT_DEFAULT;
    _gwCfg.syncIntervalMin = doc["sync_interval"] | (uint16_t)GW_SYNC_INTERVAL_DEFAULT_MIN;
    if (_gwCfg.syncIntervalMin < 1) _gwCfg.syncIntervalMin = 1;

    float f = doc["freq"].as<float>();
    _gwCfg.loraFreq = (f >= 433.0f && f <= 928.0f) ? f : LORA_FREQ_DEFAULT;

    _cfgMgr.save(_gwCfg);

    _server.send(200, "application/json", "{\"ok\":true}");
    Serial.println("[Web] Configuracion guardada. Reiniciando en 3 s...");
    _restart = true;
}

void WebPortal::_handleReset() {
    _cfgMgr.reset();
    _server.send(200, "application/json",
                 "{\"ok\":true,\"msg\":\"Configuracion reseteada\"}");
    Serial.println("[Web] Config reseteada. Reiniciando en 3 s...");
    _restart = true;
}

void WebPortal::_handleWifiApply() {
    if (!_server.hasArg("plain")) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"Sin cuerpo JSON\"}");
        return;
    }
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, _server.arg("plain"))) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"JSON invalido\"}");
        return;
    }
    String newSsid = doc["ssid"].as<String>();
    if (newSsid.isEmpty()) {
        _server.send(400, "application/json",
                     "{\"ok\":false,\"msg\":\"SSID requerido\"}");
        return;
    }
    String newPass = doc["pass"].as<String>();

    _cfgMgr.savePendingWifi(newSsid, newPass, _gwCfg.wifiSsid, _gwCfg.wifiPass);
    _gwCfg.wifiSsid = newSsid;
    _gwCfg.wifiPass = newPass;

    _server.send(200, "application/json", "{\"ok\":true}");
    Serial.printf("[Web] WiFi pendiente '%s'. Reiniciando...\n", newSsid.c_str());
    _restart = true;
}

void WebPortal::_handleNotFound() {
    // Redirigir al portal en cualquier URL desconocida (captive portal básico)
    _server.sendHeader("Location", "http://192.168.4.1/", true);
    _server.send(302, "text/plain", "");
}
