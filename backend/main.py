from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from model import predecir_escenario

app = FastAPI(title="API Predicción de Sequía en Embalses")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://front-end-unit-25.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos ---
class PeticionPrediccion(BaseModel):
    horizonte_meses: int
    escenario: str  # "normal", "seco", "muy_seco", "humedo"
    nivel_actual_usuario: Optional[float] = None

# --- Endpoints ---
@app.get("/", tags=["root"])
def root():
    return {
        "status": "ok",
        "service": "backend-unit-25",
        "message": "Backend UNIT-25 funcionando correctamente",
    }

@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": "backend-unit-25",
        "model_loaded": True,
    }

@app.post("/predict")
async def predict(req: PeticionPrediccion):
    try:
        resultado = predecir_escenario(
            horizonte_meses=req.horizonte_meses,
            escenario=req.escenario,
            nivel_actual_usuario=req.nivel_actual_usuario,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
