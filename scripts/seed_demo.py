#!/usr/bin/env python3
"""
Crea datos demo para Exalink Campo:
  1 Tenant, 1 SuperAdmin, 1 Tenant Admin, 1 Establecimiento,
  4 Potreros, 1 Rodeo, 50 Animales, 10 GPS Collares, 1 Gateway,
  100 Ubicaciones GPS, 5 Alertas, 10 Eventos Sanidad, 5 Pesajes
"""
import os, sys, asyncio, random, uuid, bcrypt
from datetime import date, datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://exalink:exalink_pass@localhost:5432/exalink_campo"
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Demo coordinates — Colonia La Esperanza, Santa Fe, Argentina
BASE_LAT = -31.70
BASE_LON = -60.80

BREEDS = ["Aberdeen Angus", "Hereford", "Brahman", "Criolla", "Limousin", "Charolais", "Simmental"]
COLORS = ["Negro", "Colorado", "Bayo", "Overo", "Moro", "Blanco"]

PADDOCKS_DEF = [
    {"name": "Potrero A1", "code": "A1", "area_ha": 45.0, "max_capacity": 15,
     "polygon": [[-60.82, -31.68], [-60.80, -31.68], [-60.80, -31.70], [-60.82, -31.70], [-60.82, -31.68]]},
    {"name": "Potrero A2", "code": "A2", "area_ha": 38.0, "max_capacity": 12,
     "polygon": [[-60.80, -31.68], [-60.78, -31.68], [-60.78, -31.70], [-60.80, -31.70], [-60.80, -31.68]]},
    {"name": "Potrero B1", "code": "B1", "area_ha": 52.0, "max_capacity": 18,
     "polygon": [[-60.82, -31.70], [-60.80, -31.70], [-60.80, -31.72], [-60.82, -31.72], [-60.82, -31.70]]},
    {"name": "Potrero B2", "code": "B2", "area_ha": 61.0, "max_capacity": 20,
     "polygon": [[-60.80, -31.70], [-60.78, -31.70], [-60.78, -31.72], [-60.80, -31.72], [-60.80, -31.70]]},
]

ANIMAL_NAMES_F = ["Manchita", "Flor", "Luna", "Bella", "Rosa", "Mora", "Tordilla", "Estrella", "Paloma", "Negra"]
ANIMAL_NAMES_M = ["Toro01", "Sampson", "Fuerte", "Bravo", "León", "Gigante", "Roble"]


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def run():

    async with SessionLocal() as db:
        # ── Tenant ──────────────────────────────────────────────────────────
        tenant_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO tenants (id, name, slug, plan, is_active, max_animals, max_devices)
            VALUES (:id, :name, :slug, :plan, true, 500, 50)
        """), {"id": tenant_id, "name": "Establecimiento Demo", "slug": "demo", "plan": "pro"})

        # ── SuperAdmin ───────────────────────────────────────────────────────
        await db.execute(text("""
            INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role)
            VALUES (:id, NULL, :email, :pw, :name, 'superadmin')
        """), {"id": uuid.uuid4(), "email": "superadmin@exalink.com", "pw": hash_pw("exalink2024"), "name": "Super Admin"})

        # ── Tenant Admin ─────────────────────────────────────────────────────
        admin_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role)
            VALUES (:id, :tid, :email, :pw, :name, 'tenant_admin')
        """), {"id": admin_id, "tid": tenant_id, "email": "admin@exalink.com", "pw": hash_pw("exalink2024"), "name": "Juan Administrador"})

        # ── Establishment ────────────────────────────────────────────────────
        est_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO establishments (id, tenant_id, name, code, province, municipality,
                total_area_ha, renspa, location, is_active, created_by)
            VALUES (:id, :tid, :name, :code, :prov, :mun, :ha, :renspa,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), true, :by)
        """), {
            "id": est_id, "tid": tenant_id, "name": "Estancia La Esperanza",
            "code": "EST-001", "prov": "Santa Fe", "mun": "Rafaela",
            "ha": 196.0, "renspa": "82-023-4-00123/00", "lat": BASE_LAT, "lon": BASE_LON, "by": admin_id
        })

        # ── Herd ─────────────────────────────────────────────────────────────
        herd_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO herds (id, tenant_id, establishment_id, name, breed)
            VALUES (:id, :tid, :eid, :name, :breed)
        """), {"id": herd_id, "tid": tenant_id, "eid": est_id, "name": "Rodeo Principal", "breed": "Aberdeen Angus"})

        # ── Paddocks ─────────────────────────────────────────────────────────
        paddock_ids = []
        for pd in PADDOCKS_DEF:
            pid = uuid.uuid4()
            paddock_ids.append(pid)
            coords = ", ".join(f"{lon} {lat}" for lon, lat in pd["polygon"])
            await db.execute(text(f"""
                INSERT INTO paddocks (id, tenant_id, establishment_id, name, code, area_ha,
                    max_capacity, current_load, status, polygon, water_source, is_active, created_by)
                VALUES (:id, :tid, :eid, :name, :code, :ha, :cap, 0, 'empty',
                    ST_SetSRID(ST_GeomFromText('POLYGON(({coords}))'), 4326), true, true, :by)
            """), {"id": pid, "tid": tenant_id, "eid": est_id, "name": pd["name"],
                   "code": pd["code"], "ha": pd["area_ha"], "cap": pd["max_capacity"], "by": admin_id})

        # ── Animals ──────────────────────────────────────────────────────────
        animal_ids = []
        paddock_assign: dict[uuid.UUID, list[uuid.UUID]] = {p: [] for p in paddock_ids}
        paddock_cycle = paddock_ids * 20

        for i in range(1, 51):
            aid = uuid.uuid4()
            animal_ids.append(aid)
            sex = "female" if i <= 40 else "male"
            breed = random.choice(BREEDS)
            name = (random.choice(ANIMAL_NAMES_F) if sex == "female" else random.choice(ANIMAL_NAMES_M)) if i <= 10 else None
            birth = date(random.randint(2018, 2023), random.randint(1, 12), random.randint(1, 28))
            weight = round(random.uniform(280, 580), 1)
            paddock_idx = (i - 1) % len(paddock_ids)
            paddock_id = paddock_ids[paddock_idx]
            paddock_assign[paddock_id].append(aid)
            cat = "vaca" if sex == "female" else "toro" if i > 45 else "novillo"

            await db.execute(text("""
                INSERT INTO animals (id, tenant_id, establishment_id, paddock_id, herd_id,
                    ear_tag, name, breed, sex, category, status, birth_date, color, weight_kg, created_by)
                VALUES (:id, :tid, :eid, :pid, :hid,
                    :tag, :name, :breed, :sex, :cat, 'active', :bd, :color, :wt, :by)
            """), {"id": aid, "tid": tenant_id, "eid": est_id, "pid": paddock_id, "hid": herd_id,
                   "tag": f"{i:03d}", "name": name, "breed": breed, "sex": sex, "cat": cat,
                   "bd": birth, "color": random.choice(COLORS), "wt": weight, "by": admin_id})

        # Update paddock current_load
        for pid, aids in paddock_assign.items():
            await db.execute(text("UPDATE paddocks SET current_load=:n, status='occupied' WHERE id=:id"),
                             {"n": len(aids), "id": pid})

        # ── Devices (10 collars + 1 gateway) ─────────────────────────────────
        device_ids = []
        collar_animal_pairs = []
        for i in range(1, 11):
            did = uuid.uuid4()
            device_ids.append(did)
            animal_id = animal_ids[i - 1]
            collar_animal_pairs.append((did, animal_id))
            pad_idx = (i - 1) % len(paddock_ids)
            paddock = PADDOCKS_DEF[pad_idx]
            plat = paddock["polygon"][0][1]
            plon = paddock["polygon"][0][0]
            lat = plat + random.uniform(0.001, 0.015)
            lon = plon + random.uniform(0.001, 0.015)
            battery = random.randint(20, 100)
            await db.execute(text("""
                INSERT INTO devices (id, tenant_id, establishment_id, animal_id, device_uid,
                    device_type, firmware, battery_pct, rssi, temperature, activity_score,
                    is_online, last_seen, last_location, is_active, created_by)
                VALUES (:id, :tid, :eid, :aid, :uid, 'gps_collar', :fw,
                    :bat, :rssi, :temp, :act, :online, :seen,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), true, :by)
            """), {
                "id": did, "tid": tenant_id, "eid": est_id, "aid": animal_id,
                "uid": f"COLLAR{i:03d}", "fw": "v2.4.1",
                "bat": battery, "rssi": random.randint(-90, -60),
                "temp": round(random.uniform(20, 35), 1),
                "act": random.randint(20, 80),
                "online": random.random() > 0.1,
                "seen": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 30)),
                "lat": lat, "lon": lon, "by": admin_id
            })

        # Gateway
        gw_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO devices (id, tenant_id, establishment_id, device_uid, device_type,
                firmware, battery_pct, is_online, last_seen, last_location, is_active, created_by)
            VALUES (:id, :tid, :eid, 'GATEWAY001', 'gateway',
                'v1.2.0', 100, true, :seen,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), true, :by)
        """), {"id": gw_id, "tid": tenant_id, "eid": est_id,
               "seen": datetime.now(timezone.utc), "lat": BASE_LAT, "lon": BASE_LON, "by": admin_id})

        # ── GPS Locations (10 tracks × 10 points) ────────────────────────────
        now = datetime.now(timezone.utc)
        for did, aid in collar_animal_pairs:
            result = await db.execute(text("SELECT last_location FROM devices WHERE id=:id"), {"id": did})
            row = result.fetchone()
            if row and row[0]:
                import re
                wkb_str = str(row[0])
                lon_off = random.uniform(-0.002, 0.002)
                lat_off = random.uniform(-0.002, 0.002)
                lat = BASE_LAT + lat_off
                lon = BASE_LON + lon_off

            for j in range(10):
                ts = now - timedelta(minutes=j * 10)
                lat_j = lat + random.uniform(-0.001, 0.001)
                lon_j = lon + random.uniform(-0.001, 0.001)
                await db.execute(text("""
                    INSERT INTO locations (id, tenant_id, device_id, animal_id, timestamp, point,
                        battery_pct, rssi, temperature, activity_score)
                    VALUES (:id, :tid, :did, :aid, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        :bat, :rssi, :temp, :act)
                """), {
                    "id": uuid.uuid4(), "tid": tenant_id, "did": did, "aid": aid,
                    "ts": ts, "lat": lat_j, "lon": lon_j,
                    "bat": random.randint(20, 100), "rssi": random.randint(-90, -60),
                    "temp": round(random.uniform(20, 35), 1),
                    "act": random.randint(10, 90)
                })

        # ── Alerts ───────────────────────────────────────────────────────────
        # Seed alerts are commented out — real alerts are generated by the
        # device monitor hook and MQTT consumer.
        # alert_defs = [
        #     ...
        # ]
        # for al in alert_defs:
        #     await db.execute(...)

        # ── Health events ─────────────────────────────────────────────────────
        vaccines = ["Aftosa", "Brucelosis", "Carbunclo", "IBR-DVB", "Clostridiosis"]
        for i in range(10):
            ev_date = date.today() - timedelta(days=random.randint(10, 120))
            next_date = ev_date + timedelta(days=180)
            await db.execute(text("""
                INSERT INTO health_events (id, tenant_id, animal_id, establishment_id,
                    event_type, product_name, dose, event_date, next_date, vet_name)
                VALUES (:id, :tid, :aid, :eid, 'vaccine', :prod, '2 ml IM', :ed, :nd, 'Dr. García')
            """), {"id": uuid.uuid4(), "tid": tenant_id, "aid": animal_ids[i],
                   "eid": est_id, "prod": random.choice(vaccines), "ed": ev_date, "nd": next_date})

        # ── Weight records ────────────────────────────────────────────────────
        for i in range(5):
            wr_date = date.today() - timedelta(days=random.randint(5, 60))
            await db.execute(text("""
                INSERT INTO weight_records (id, tenant_id, animal_id, weight_kg, measure_date, method, daily_gain)
                VALUES (:id, :tid, :aid, :w, :d, 'Balanza electrónica', :gdp)
            """), {"id": uuid.uuid4(), "tid": tenant_id, "aid": animal_ids[i],
                   "w": round(random.uniform(300, 600), 1), "d": wr_date,
                   "gdp": round(random.uniform(0.6, 1.4), 3)})

        # ── Reproduction events ───────────────────────────────────────────────
        for i in range(5):
            ev_date = date.today() - timedelta(days=random.randint(30, 180))
            await db.execute(text("""
                INSERT INTO reproduction_events (id, tenant_id, animal_id, event_type, event_date,
                    is_pregnant, expected_birth_date, vet_name)
                VALUES (:id, :tid, :aid, 'pregnancy_check', :ed, :preg, :ebd, 'Dr. Rodríguez')
            """), {"id": uuid.uuid4(), "tid": tenant_id, "aid": animal_ids[i],
                   "ed": ev_date, "preg": True,
                   "ebd": ev_date + timedelta(days=280)})

        await db.commit()
        print("✅  Datos demo creados:")
        print(f"    Tenant: Establecimiento Demo (demo)")
        print(f"    Admin:  admin@exalink.com / exalink2024")
        print(f"    Super:  superadmin@exalink.com / exalink2024")
        print(f"    Animales: 50 | Potreros: 4 | Dispositivos: 11 | Alertas: 5")


if __name__ == "__main__":
    asyncio.run(run())
