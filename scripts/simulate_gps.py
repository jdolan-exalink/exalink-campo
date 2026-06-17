#!/usr/bin/env python3
"""
Simula mensajes GPS via MQTT para los 10 collares demo.
Ejecutar: python scripts/simulate_gps.py
"""
import os, sys, asyncio, json, random
from datetime import datetime, timezone

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TENANT_SLUG = "demo"
INTERVAL = 30  # segundos entre envíos

COLLARS = [f"COLLAR{i:03d}" for i in range(1, 11)]

# Starting positions (approximate Santa Fe area)
positions = {
    collar: {
        "lat": -31.70 + random.uniform(-0.02, 0.02),
        "lon": -60.80 + random.uniform(-0.02, 0.02),
        "battery": random.randint(30, 100),
    }
    for collar in COLLARS
}


async def simulate():
    import aiomqtt
    print(f"Iniciando simulación GPS → {MQTT_HOST}:{MQTT_PORT}")
    print(f"Intervalo: {INTERVAL}s | Dispositivos: {len(COLLARS)}")

    async with aiomqtt.Client(hostname=MQTT_HOST, port=MQTT_PORT) as client:
        print("MQTT conectado. Enviando ubicaciones...")
        tick = 0
        while True:
            for collar in COLLARS:
                pos = positions[collar]
                # Random walk
                pos["lat"] += random.uniform(-0.0003, 0.0003)
                pos["lon"] += random.uniform(-0.0003, 0.0003)
                # Battery drains slowly
                if tick % 10 == 0 and pos["battery"] > 5:
                    pos["battery"] -= random.randint(0, 2)

                payload = {
                    "device_id": collar,
                    "lat": round(pos["lat"], 6),
                    "lon": round(pos["lon"], 6),
                    "battery": pos["battery"],
                    "rssi": random.randint(-90, -55),
                    "temperature": round(random.uniform(18, 38), 1),
                    "activity_score": random.randint(5, 95),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                topic = f"exalink/{TENANT_SLUG}/devices/{collar}/location"
                await client.publish(topic, json.dumps(payload))
                print(f"  {collar}: lat={payload['lat']:.4f} lon={payload['lon']:.4f} bat={payload['battery']}%")

            tick += 1
            await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(simulate())
