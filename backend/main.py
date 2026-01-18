"""
main.py - Archivo principal de la API FastAPI
==============================================

Propósito:
- Configura e inicia la aplicación FastAPI
- Expone los endpoints REST del servicio
- Maneja las peticiones HTTP entrantes

Endpoints disponibles:
- GET /health: Verifica el estado de la API
- POST /predict: Recibe parámetros de predicción y devuelve resultados

Dependencias:
- FastAPI: Framework web
- Uvicorn: Servidor ASGI

La lógica del modelo Prophet está separada en model.py
para mantener una arquitectura limpia y escalable.
"""

# Aquí irá la importación y configuración de FastAPI
# La lógica se implementará importando funciones de model.py


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from model import predecir_escenario


app = FastAPI(title="API Predicción de Sequía en Embalses")

@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": "backend-unit-25",
        "model_loaded": True
    }


# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",          # Live Server típico
        "http://127.0.0.1:5500",
        "http://localhost:3000",          # otros posibles dev servers
        "http://127.0.0.1:3000",
        "https://front-end-unit-25.vercel.app",  # Vercel (sin barra final)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PeticionPrediccion(BaseModel):
    horizonte_meses: int
    escenario: str  # "normal", "seco", "muy_seco", "humedo"
    nivel_actual_usuario: Optional[float] = None


@app.get("/health")
async def health():
    return {"status": "ok", "message": "API de sequía funcionando"}


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
