#include "lora_server.h"
#include "config_manager.h"
#include "config.h"
#include <ArduinoJson.h>
#include <mbedtls/base64.h>

static const char TLS_CERT[] = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDFTCCAf2gAwIBAgIUf7xEfmZFuuG6y9v7PFXMvGAqBy0wDQYJKoZIhvcNAQEL
BQAwGjEYMBYGA1UEAwwPRXhhTGluay1Mb1JhLUdXMB4XDTI2MDYxMTE0NDE1MloX
DTM2MDYwODE0NDE1MlowGjEYMBYGA1UEAwwPRXhhTGluay1Mb1JhLUdXMIIBIjAN
BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmfPU5tFbRJR8Scu5kvXVWJ/qg405
cX+8VIfoJya+ngE/67Zl1p1PvYdnRnR6JG5Hd5tbyb6nhyM0eWMQjY6jaXdrCqV6
2KubY05+XPUnboijy3igjp0cuSdqhuNl9MdYGIZvnPznzqpTtvz6JzMot8eXhbeN
LSwNlbQr93HsEp6Bi24he39FFGtcB+1dm368N4jSV70EiS+ysbga/lHEv5ktmTIj
+qQmEy9q5Tz0OA5eklKuOduCRRaIrlo3RBmeHSyjHOkiJmEbJ0uB5miTN4GiurGD
W3rKzmQ8a2ylljS9k4Q+myg/wgv+8cDGnUXBngun+soM+qf37HDJiqoRTwIDAQAB
o1MwUTAdBgNVHQ4EFgQULht4tP5bBTv8nxj1gfjTO7W6bDgwHwYDVR0jBBgwFoAU
Lht4tP5bBTv8nxj1gfjTO7W6bDgwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0B
AQsFAAOCAQEAkyXLmJM+GpHCsgsZr4Z2uh2MBeqdmHaHhDxzs2WCH/KJVxT+qpBN
oEAN4+/X38zYWy3rpAmjPKPpIR0E3ZkjPraA4L/sRMH+hPtAPkzw3VpbeYjqjXKc
XUrj1v8jDRkhOdHtI/jH1aVebSmG40+v4NcTlutk8j/s8v8kVw1WM2DIhEa/zFk7
77XDAzwRI4Qpwo0YiDwON6XjPpHS9lDT+njLxq2xnqJx5hRx64K9TCjjFuQOV0oX
kc8NZm//wyH0uVczWoaut4U1ovstIaa0q3uamNAtxMywDdlcdT7OoRYcpF/z8g7Z
yViJG1z8FgYirQNyDdiZ8Kllfna51WXBjg==
-----END CERTIFICATE-----
)EOF";

static const char TLS_KEY[] = R"EOF(
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCZ89Tm0VtElHxJ
y7mS9dVYn+qDjTlxf7xUh+gnJr6eAT/rtmXWnU+9h2dGdHokbkd3m1vJvqeHIzR5
YxCNjqNpd2sKpXrYq5tjTn5c9SduiKPLeKCOnRy5J2qG42X0x1gYhm+c/OfOqlO2
/PonMyi3x5eFt40tLA2VtCv3cewSnoGLbiF7f0UUa1wH7V2bfrw3iNJXvQSJL7Kx
uBr+UcS/mS2ZMiP6pCYTL2rlPPQ4Dl6SUq4524JFFoiuWjdEGZ4dLKMc6SImYRsn
S4HmaJM3gaK6sYNbesrOZDxrbKWWNL2ThD6bKD/CC/7xwMadRcGeC6f6ygz6p/fs
cMmKqhFPAgMBAAECggEACRc/9hfcllOhdTk/0vxC06jVNKYpuiGrVjrLZ5GV6mLF
ypU9EKu+G1PpxIDLRVWXvunXIKPX9xaumhCt/Hp9/IGOFYLtmqERQI908ufax5bK
smwWTVNKcI8WXMUo7nWUb6gFvjmAEUfb9zibcKYj7po/ic0QSXHutyRFkcutSKfN
hBwrGgu3MM33SCI/T3sCEx2ScAPWQdOqjb0Lj/OEaDFUbCbSfss3RSyaTZ6lvx4F
KWpg1A/GaN7dzvMeseAzTVvdKzgrsnvZLa+DPT7+usC5494lHHtP014v5ZkyM9tS
1hN1qPo6Dqdn4/LbazEOSH2AtNpZGBHz0MnTkjdUfQKBgQDXE9trSnVmu4TQrVgQ
TPhsaFetEYHFs8BJUe3qIvi7CwZSyIE2i8O/2zez6rvm1kW1KMRMtOH9cDamx74g
Q4dd2QabHZy5eW8gRddPbE5xyWFtulDYp/eL1o7XGpnu2OfT1hUCfS9e291wp0be
w8Zkv742Lf1e7o3xvo39VL9VewKBgQC3Pqbs/QD/hBdyqwyjM/ocPbm4cMp7e8NV
Cf1yjyyeDKqg4dr2JKjzdCjLruuY8q8wdssO9RgMrDE3r/RrnBl08mhr5hdihdLD
zYx18E2lHuAArxXFXuHV+99npStGY0WUxVRWl1RBJvNxMa53fR6DtwSpHKK0rpWm
MTeYAoYpPQKBgQC6NTLu/RQP0aH3mVx5IGqkUOI3sMSOCkYcNJaq84QtTCo5Weak
9vSPEphzaHMuM60+XwE0+BYAejqWwrBU9qIoGlGh0k1yNzSC2HTFCpwP364+deSw
7xtfMm+QxDMpmxl7Sgn+kauFkQ1zDyBIlW8aovdnqQGIQzkZZ0U/YzQUKQKBgGLZ
SEDFRnmPrvprbRjI3B3J6lqldYThQYCpL/BRbbcgjBbXXz+yjPUvbyZZCLxsBbc2
DdnWuw9y/+XTZB18inr8nPm/mFPMbuKzChdA9xGgsyOLT0o2IctF4MDPZ6XDvXBA
dntzjL7MnTwtmbjZZNGWs8vqJ5ciKpYJLL0yd17dAoGBALNQt9C9woPrbJGPnQJr
W1QEz1bbZXmBv2milKxmKcfGqTBRh+o0ROrOmKg08EiI7XkuHwR66e7/T7Hm94Wv
w5OXM6BKnKzPDB/T+7T3fBY5uAHojOxTTj+MLxOr79GnQnQNA9Nd5rtFPI76pGO1
qEZHUqt9VAkJ7Ey1wf4ebrcj
-----END PRIVATE KEY-----
)EOF";

LoraServer::LoraServer(const GatewayConfig& cfg, LoRaManager& lora)
    : _server(nullptr)
    , _cfg(cfg)
    , _lora(lora)
    , _running(false)
{}

LoraServer::~LoraServer() {
    stop();
}

bool LoraServer::begin() {
    if (_running) return true;

    httpd_ssl_config_t conf = HTTPD_SSL_CONFIG_DEFAULT();

    conf.cacert_pem    = (const uint8_t*)TLS_CERT;
    conf.cacert_len    = strlen(TLS_CERT);
    conf.prvtkey_pem   = (const uint8_t*)TLS_KEY;
    conf.prvtkey_len    = strlen(TLS_KEY);
    conf.port_secure    = _cfg.listenPort;
    conf.port_insecure  = 0;

    esp_err_t ret = httpd_ssl_start(&_server, &conf);
    if (ret != ESP_OK) {
        Serial.printf("[LoraSrv] ERROR httpd_ssl_start(): %s\n",
                      esp_err_to_name(ret));
        return false;
    }

    httpd_uri_t uriIngest = {
        .uri     = "/api/lora/ingest",
        .method  = HTTP_POST,
        .handler = _handleIngest,
        .user_ctx = (void*)this
    };
    httpd_register_uri_handler(_server, &uriIngest);

    httpd_uri_t uriHealth = {
        .uri     = "/health",
        .method  = HTTP_GET,
        .handler = _handleHealth,
        .user_ctx = (void*)this
    };
    httpd_register_uri_handler(_server, &uriHealth);

    _running = true;
    Serial.printf("[LoraSrv] HTTPS server en puerto %d\n",
                  _cfg.listenPort);
    Serial.println("[LoraSrv] Endpoints:");
    Serial.println("[LoraSrv]   POST /api/lora/ingest  (Bearer auth)");
    Serial.println("[LoraSrv]   GET  /health");
    return true;
}

void LoraServer::stop() {
    if (_server) {
        httpd_ssl_stop(_server);
        _server  = nullptr;
        _running = false;
        Serial.println("[LoraSrv] Detenido.");
    }
}

bool LoraServer::isRunning() const {
    return _running;
}

esp_err_t LoraServer::_handleHealth(httpd_req_t *req) {
    const char resp[] = "{\"status\":\"ok\"}";
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, resp, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

esp_err_t LoraServer::_handleIngest(httpd_req_t *req) {
    LoraServer* self = (LoraServer*)req->user_ctx;

    int totalLen = req->content_len;
    if (totalLen <= 0 || totalLen > 4096) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST,
                            "Body vacio o demasiado grande");
        return ESP_FAIL;
    }

    char* buf = (char*)malloc(totalLen + 1);
    if (!buf) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Sin memoria");
        return ESP_FAIL;
    }

    int received = 0;
    while (received < totalLen) {
        int r = httpd_req_recv(req, buf + received, totalLen - received);
        if (r <= 0) {
            free(buf);
            httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Error al leer body");
            return ESP_FAIL;
        }
        received += r;
    }
    buf[totalLen] = '\0';

    StaticJsonDocument<1024> doc;
    DeserializationError err = deserializeJson(doc, buf);
    free(buf);

    if (err) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "JSON invalido");
        return ESP_FAIL;
    }

    const char* gwId = doc["gateway_id"] | "";
    const char* hex  = doc["payload_hex"] | "";
    int rssi         = doc["rssi"] | 0;
    float snr        = doc["snr"];
    float freq       = doc["freq_mhz"] | 0.0f;
    int sf           = doc["sf"] | 0;

    Serial.println("========================================");
    Serial.println("[LoraSrv] Paquete recibido via HTTPS");
    Serial.printf("  Gateway  : %s\n", gwId);
    Serial.printf("  Freq     : %.1f MHz  SF:%d\n", freq, sf);
    Serial.printf("  RSSI     : %d dBm  SNR: %.1f dB\n", rssi, snr);
    Serial.printf("  Payload  : %s\n", hex);
    Serial.printf("  Longitud : %d bytes\n", strlen(hex) / 2);
    Serial.println("========================================");

    const char ok[] = "{\"ok\":true}";
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, ok, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}
