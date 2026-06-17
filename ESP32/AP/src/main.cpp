#include <Arduino.h>
#include <time.h>
#include "config.h"
#include "config_manager.h"
#include "display_manager.h"
#include "wifi_manager.h"
#include "web_portal.h"
#include "lora_manager.h"
#include "http_client.h"
#include "lora_server.h"
#include "gps_manager.h"
#include "gateway_sync.h"

// ─────────────────────────────────────────────────────────────
// Objetos globales
// ─────────────────────────────────────────────────────────────
static GatewayConfig  gwCfg;
static ConfigManager  cfgMgr;
static DisplayManager display;
static WiFiManager    wifiMgr;
static LoRaManager    loraMgr;
static GpsManager     gpsMgr;
static WebPortal*     portal   = nullptr;
static LoraServer*    loraSrv  = nullptr;

static bool loraOK = false;
static bool wifiOK = false;

// ── Sync periódico ────────────────────────────────────────────
static uint32_t  _lastSyncMs        = 0;
static int32_t   _lastSyncLatencyMs = -1;

// ── Contadores / reset diario via NTP ─────────────────────────
static int32_t   _todayDayNum       = -1;   // día UTC actual (time/86400), -1 = sin NTP

static void initNTP() {
    configTime(-3 * 3600, 0, "pool.ntp.org", "time.nist.gov");
    Serial.println("[NTP] Sincronizando hora...");
}

static void checkDayReset() {
    time_t now = time(nullptr);
    if (now < 86400) return;   // NTP todavía no sincronizó
    int32_t dayNum = (int32_t)(now / 86400);
    if (_todayDayNum < 0) {
        _todayDayNum = dayNum;   // primera lectura
        return;
    }
    if (dayNum != _todayDayNum) {
        _todayDayNum = dayNum;
        if (portal) portal->resetDailyStats();
        Serial.println("[Stats] Nuevo día — contadores diarios reseteados.");
    }
}

static String buildSrvLine() {
    if (!portal || !portal->isServerTested()) return "SRV: --";
    if (!portal->isServerOk()) return "SRV: ERR";
    if (_lastSyncLatencyMs >= 0)
        return "SRV: OK " + String(_lastSyncLatencyMs) + "ms";
    return "SRV: OK";
}

static void doGatewaySync() {
    if (!wifiMgr.isSTAConnected()) return;
    GatewayStatus st;
    GpsData gps = gpsMgr.getData();
    st.gpsValid    = gps.valid;
    st.lat         = gps.lat;
    st.lon         = gps.lon;
    st.wifiSsid    = gwCfg.wifiSsid;
    st.wifiRssi    = WiFi.RSSI();
    st.name        = gwCfg.gatewayName;
    st.batteryPct  = readBatteryPct();
    st.uptimeSec   = millis() / 1000;
    st.pktsTotal   = loraMgr.getPacketCount();

    String newName;
    uint32_t t0 = millis();
    bool ok = syncGateway(gwCfg.serverUrl, gwCfg.gatewayId,
                          gwCfg.lorawanPass, st, newName);
    _lastSyncLatencyMs = ok ? (int32_t)(millis() - t0) : -1;
    if (portal) portal->setServerOk(ok, _lastSyncLatencyMs);

    if (ok && newName.length() > 0 && newName != gwCfg.gatewayName) {
        gwCfg.gatewayName = newName;
        cfgMgr.save(gwCfg);
        Serial.printf("[Sync] Nombre del GW actualizado: '%s'\n", newName.c_str());
    }
    _lastSyncMs = millis();
}

// ─────────────────────────────────────────────────────────────
static String buildAPSSID() {
    uint64_t id = ESP.getEfuseMac();
    char suf[8];
    snprintf(suf, sizeof(suf), "%04X", (uint16_t)(id >> 32));
    return String(AP_SSID_PREFIX) + suf;
}

// ─────────────────────────────────────────────────────────────
// setup()
// ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(600);
    Serial.println("\n=======================================");
    Serial.println("   EXALINK LORA GATEWAY — Iniciando");
    Serial.println("=======================================");

    // 1 ── OLED ────────────────────────────────────────────────
    display.begin();
    display.showTitle();
    delay(1200);

    // 2 ── Configuración NVS ───────────────────────────────────
    cfgMgr.begin();
    cfgMgr.load(gwCfg);
    Serial.printf("[Config] GW ID    : %s\n", gwCfg.gatewayId.c_str());
    Serial.printf("[Config] WiFi SSID: %s\n", gwCfg.wifiSsid.c_str());
    Serial.printf("[Config] Servidor : %s\n", gwCfg.serverUrl.c_str());
    Serial.printf("[Config] LoRa     : %.1f MHz\n", gwCfg.loraFreq);
    Serial.printf("[Config] Listen   : puerto %d\n", gwCfg.listenPort);

    // 3 ── GPS ────────────────────────────────────────────────
    gpsMgr.begin();

    // 3b ── LoRa ───────────────────────────────────────────────
    display.showStatus("Iniciando LoRa...",
                       String(gwCfg.loraFreq, 1) + " MHz");
    delay(300);
    loraOK = loraMgr.begin(gwCfg.loraFreq);
    if (!loraOK) {
        Serial.println("[ERROR] LoRa no inicializado — verificar hardware.");
        display.showStatus("ERROR: LoRa fail", "Verificar hardware");
        delay(2000);
    }

    // 4 ── WiFi ────────────────────────────────────────────────
    if (cfgMgr.hasPendingWifi()) {
        display.showStatus("Probando WiFi:", gwCfg.wifiSsid, "Fallback activo");
        Serial.printf("[WiFi] Test nueva red '%s'...\n", gwCfg.wifiSsid.c_str());
        wifiOK = wifiMgr.connectSTA(gwCfg.wifiSsid, gwCfg.wifiPass, 20000);
        if (wifiOK) {
            cfgMgr.commitPendingWifi();
            Serial.printf("[WiFi] Nueva red OK. IP: %s\n", wifiMgr.getLocalIP().c_str());
        } else {
            Serial.println("[WiFi] Nueva red falló — revirtiendo.");
            cfgMgr.revertWifi(gwCfg);
            display.showStatus("WiFi FAIL", "Volviendo anterior...");
            delay(800);
            wifiOK = wifiMgr.connectSTA(gwCfg.wifiSsid, gwCfg.wifiPass,
                                         WIFI_CONNECT_TIMEOUT_MS);
        }
    } else {
        display.showStatus("Conectando WiFi:", gwCfg.wifiSsid);
        Serial.printf("[WiFi] Intentando '%s' por %d s...\n",
                      gwCfg.wifiSsid.c_str(), WIFI_CONNECT_TIMEOUT_MS / 1000);
        wifiOK = wifiMgr.connectSTA(gwCfg.wifiSsid, gwCfg.wifiPass,
                                     WIFI_CONNECT_TIMEOUT_MS);
    }

    if (wifiOK) {
        String ip = wifiMgr.getLocalIP();
        display.showStatus("WiFi OK", ip);
        Serial.printf("[WiFi] Conectado. IP: %s\n", ip.c_str());
        wifiMgr.enableReconnect(gwCfg.wifiSsid, gwCfg.wifiPass);
        initNTP();
        delay(1000);
    } else {
        display.showStatus("WiFi FAIL", "Iniciando AP...");
        Serial.println("[WiFi] Fallo — iniciando modo AP.");
        delay(800);

        String apSSID = buildAPSSID();
        wifiMgr.startAP(apSSID);

        display.showStatus("Modo AP activo",
                           "AP: " + apSSID,
                           "IP: " + String(AP_IP_ADDR));
        Serial.printf("[WiFi] AP listo: %s | IP: %s\n",
                      apSSID.c_str(), AP_IP_ADDR);
        delay(1500);
    }

    // 5 ── Web portal (activo siempre) ─────────────────────────
    portal = new WebPortal(cfgMgr, gwCfg, loraMgr);
    portal->begin();

    // 5b ── Primera sincronización con servidor ────────────────
    if (wifiOK) {
        display.showStatus("Sincronizando...", gwCfg.serverUrl.substring(0,22));
        doGatewaySync();
    }

    // 6 ── LoRaWAN HTTPS listener ───────────────────────────────
    loraSrv = new LoraServer(gwCfg, loraMgr);
    if (loraSrv->begin()) {
        Serial.printf("[Main] LoRaWAN HTTPS listener en puerto %d\n",
                      gwCfg.listenPort);
    } else {
        Serial.println("[Main] ERROR: No se pudo iniciar el servidor HTTPS LoRaWAN.");
    }

    // 7 ── Estado final ────────────────────────────────────────
    {
        String l1   = (gwCfg.gatewayName.length() > 0 ? gwCfg.gatewayName : "GW-EXA")
                      + "  " + wifiMgr.getLocalIP();
        String l2   = gwCfg.gatewayId;
        String l4   = buildSrvLine();
        if (loraOK) {
            display.showStatus(l1, l2, String(gwCfg.loraFreq, 1) + " MHz", l4);
        } else {
            display.showStatus("LoRa: ERROR", l2, "Revisar hardware", l4);
        }
    }

    Serial.println("[Setup] Listo.\n");
}

// ─────────────────────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────────────────────
static uint32_t _lastDispRefresh = 0;

void loop() {
    // ── GPS (leer UART frecuentemente) ────────────────────────
    gpsMgr.update();

    // ── Reset diario de estadísticas ─────────────────────────
    checkDayReset();

    // ── Force sync pedido desde web portal ────────────────────
    if (portal && portal->shouldForceSync()) {
        portal->clearForceSync();
        doGatewaySync();
    }

    // ── Sync periódico según intervalo configurado ────────────
    uint32_t syncIntervalMs = (uint32_t)gwCfg.syncIntervalMin * 60UL * 1000UL;
    if (wifiMgr.isSTAConnected() &&
        millis() - _lastSyncMs >= syncIntervalMs) {
        doGatewaySync();
    }

    // ── Web server ────────────────────────────────────────────
    if (portal) {
        portal->handle();
        if (portal->shouldRestart()) {
            if (loraSrv) { loraSrv->stop(); delete loraSrv; loraSrv = nullptr; }
            display.showStatus("Guardando...", "Reiniciando en 3 s");
            delay(3000);
            ESP.restart();
        }
    }

    // ── WiFi reconexión automática (modo STA) ─────────────────
    wifiMgr.handleReconnect();

    // ── Refresco periódico pantalla cada 5 s ──────────────────
    if (millis() - _lastDispRefresh >= 5000) {
        _lastDispRefresh = millis();
        String l1 = (gwCfg.gatewayName.length() > 0 ? gwCfg.gatewayName : "GW-EXA")
                    + "  " + wifiMgr.getLocalIP();
        String l2 = gwCfg.gatewayId;
        String l4 = buildSrvLine();
        if (loraOK) {
            String l3 = String(gwCfg.loraFreq, 1) + " MHz  #" +
                        String(loraMgr.getPacketCount());
            display.showStatus(l1, l2, l3, l4);
        } else {
            display.showStatus("LoRa: ERROR", l2, "Revisar hardware", l4);
        }
    }

    // ── Paquete LoRa disponible? ──────────────────────────────
    if (loraOK && loraMgr.available()) {
        LoRaPacket pkt = loraMgr.getPacket();

        if (pkt.payloadHex.length() == 0) return;   // error de lectura

        // Armar preview: DevAddr para uplinks LoRaWAN, hex corto para resto
        String preview;
        if (pkt.isLoRaWAN && (pkt.mtype == 0x40 || pkt.mtype == 0x80)) {
            char buf[20];
            snprintf(buf, sizeof(buf), "Dev:%08X", pkt.devAddr);
            preview = buf;
        } else {
            preview = pkt.payloadHex.substring(0, 21);
        }
        display.showLoRaPacket(pkt.rssi, pkt.snr,
                               loraMgr.getPacketCount(), preview);
        _lastDispRefresh = millis();   // evitar sobreescritura por el refresh

        // Enviar por HTTP si hay WiFi
        if (wifiMgr.isSTAConnected()) {
            bool ok = httpPostLoRaPacket(
                gwCfg.serverUrl,
                gwCfg.gatewayId,
                gwCfg.lorawanPass,
                pkt,
                gwCfg.loraFreq,
                LORA_SF_DEFAULT,
                LORA_BW_DEFAULT
            );
            if (portal) {
                portal->setServerOk(ok, -1);
                portal->incDailyPkt(ok);
            }

            if (!ok) {
                display.showStatus("HTTP ERR",
                                   "Pkt #" + String(loraMgr.getPacketCount()),
                                   gwCfg.serverUrl.substring(0, 22));
                delay(1000);
                display.showLoRaPacket(pkt.rssi, pkt.snr,
                                       loraMgr.getPacketCount(), preview);
                _lastDispRefresh = millis();
            }
        } else {
            Serial.println("[HTTP] Sin WiFi — paquete no enviado.");
        }
    }
}
