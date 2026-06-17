from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.animal import Animal, AnimalSex, AnimalStatus
from app.models.weight import WeightRecord
from app.models.health import HealthEvent, HealthEventType
import io
import uuid
from datetime import date

router = APIRouter(prefix="/import", tags=["import"])


def _parse_date(val) -> date | None:
    if not val or str(val).strip() == "":
        return None
    try:
        if hasattr(val, "date"):
            return val.date()
        return date.fromisoformat(str(val).strip())
    except Exception:
        return None


@router.post("/animals")
async def import_animals(
    file: UploadFile = File(...),
    establishment_id: uuid.UUID = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    import pandas as pd

    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Error leyendo archivo: {e}")

    required = {"ear_tag", "sex"}
    if not required.issubset(set(df.columns.str.lower())):
        raise HTTPException(400, f"Columnas requeridas: {required}")

    df.columns = df.columns.str.lower().str.strip()

    created = 0
    errors = []
    for i, row in df.iterrows():
        try:
            sex_val = str(row.get("sex", "")).strip().lower()
            sex = AnimalSex.FEMALE if sex_val in ("female", "hembra", "f", "h") else AnimalSex.MALE
            animal = Animal(
                tenant_id=current_user.tenant_id,
                establishment_id=establishment_id,
                created_by=current_user.id,
                ear_tag=str(row["ear_tag"]).strip(),
                sex=sex,
                name=str(row["name"]).strip() if "name" in row and row["name"] else None,
                breed=str(row["breed"]).strip() if "breed" in row and row["breed"] else None,
                birth_date=_parse_date(row.get("birth_date")),
                weight_kg=float(row["weight_kg"]) if "weight_kg" in row and row["weight_kg"] else None,
                notes=str(row["notes"]).strip() if "notes" in row and row["notes"] else None,
            )
            db.add(animal)
            created += 1
        except Exception as e:
            errors.append({"row": i + 2, "error": str(e)})

    await db.flush()
    return {"created": created, "errors": errors, "total_rows": len(df)}


@router.get("/template/animals")
async def download_animal_template():
    import pandas as pd
    from fastapi.responses import StreamingResponse

    df = pd.DataFrame({
        "ear_tag": ["001", "002"],
        "sex": ["female", "male"],
        "name": ["Manchita", "Toro01"],
        "breed": ["Aberdeen Angus", "Hereford"],
        "birth_date": ["2022-03-15", "2021-08-20"],
        "weight_kg": [380, 520],
        "notes": ["", ""],
    })
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_animales.xlsx"},
    )
