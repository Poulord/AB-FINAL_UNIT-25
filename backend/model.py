"""
model.py - Lógica del modelo Prophet para predicción de sequías
================================================================

Propósito:
- Cargar datos históricos de embalses desde CSV
- Entrenar el modelo Prophet una sola vez en la inicialización
- Generar predicciones de volumen embalsado para diferentes horizontes
- Aplicar escenarios climáticos (normal, seco, muy_seco, húmedo)
- Clasificar el riesgo de sequía basado en umbrales históricos

Flujo de ejecución:
1. Al importar este módulo, se cargan automáticamente los datos históricos
2. Se entrena el modelo Prophet (almacenado globalmente)
3. Se calculan umbrales de riesgo (p10, p25)
4. Las funciones están listas para ser llamadas desde main.py

Funciones principales:
- cargar_datos_historicos(): Carga CSV y valida estructura
- entrenar_modelo(): Entrena Prophet y almacena en variable global
- predecir_escenario(): Función principal que orquesta todo el pipeline
- aplicar_escenario(): Multiplica predicciones por factor de escenario
- clasificar_riesgo(): Asigna categorías de riesgo (BAJO, MODERADO, ALTO, CRÍTICO)

Dependencias:
- pandas: Manipulación de DataFrames
- numpy: Operaciones numéricas
- prophet: Modelo de series temporales
"""

# Aquí irán las funciones del modelo
# Se importarán en main.py para exponer a través de la API



"""
model.py - Módulo de predicción de sequías con Prophet
========================================================

Este módulo implementa un sistema completo de predicción de volumen embalsado
y clasificación de riesgo de sequía para múltiples embalses. Integra:

  - Carga y transformación de datos históricos
  - Entrenamiento de modelo Prophet
  - Generación de forecasts con escenarios climáticos
  - Calibración según niveles actuales del usuario
  - Clasificación de riesgo de sequía
  - Construcción de respuestas serializables a JSON

Uso principal:
  >>> respuesta = predecir_escenario(
  ...     horizonte_meses=12,
  ...     escenario='seco',
  ...     nivel_actual_usuario=810.0
  ... )
  >>> print(respuesta)

Requisitos:
  - pandas
  - numpy
  - prophet
"""

import pandas as pd
import numpy as np
from pathlib import Path
from prophet import Prophet
import logging
from typing import Optional, Tuple, Dict, Any

# Configurar logging
logging.basicConfig(level=logging.WARNING)

# ============================================================================
# CONSTANTES GLOBALES Y CONFIGURACIÓN
# ============================================================================

# TODO: Ajustar según la ubicación real del archivo CSV en el proyecto
DATA_FILE = Path(__file__).parent / "data" / "embalses_limpio_final.csv"

# Variables globales para el modelo
MODEL: Optional[Prophet] = None
DF_ANUAL_PRED: Optional[pd.DataFrame] = None
DF_ESCENARIOS: Optional[pd.DataFrame] = None
UMBRALES: Dict[str, float] = {}
Y_ULTIMO_REAL: Optional[float] = None

# ============================================================================
# FUNCIONES DE INICIALIZACIÓN Y CARGA DE DATOS
# ============================================================================

def cargar_datos_historicos(ruta_csv: str) -> pd.DataFrame:
    """
    Carga datos históricos limpios de embalses desde CSV.
    
    TODO: Esta función asume que el CSV tiene columnas 'fecha' y 'total'.
    Si la estructura del CSV es diferente, ajusta los nombres de columnas.
    
    Parámetros
    ----------
    ruta_csv : str
        Ruta al archivo CSV con datos históricos limpios
        (debe contener al menos columnas: 'fecha', 'total')
    
    Retorna
    -------
    pd.DataFrame
        DataFrame pivotado con columnas 'fecha' y 'total'
    
    Raises
    ------
    FileNotFoundError
        Si el archivo CSV no existe
    ValueError
        Si el CSV no contiene las columnas esperadas
    """
    ruta = Path(ruta_csv)
    
    if not ruta.exists():
        raise FileNotFoundError(
            f"Archivo no encontrado: {ruta}\n"
            f"Verifica que exista en: {ruta.absolute()}"
        )
    
    # TODO: Si el CSV tiene separador diferente, cambia el parámetro 'sep'
    df = pd.read_csv(ruta, encoding="utf-8")
    
    # Validar columnas requeridas
    requeridas = {"fecha", "total"}
    if not requeridas.issubset(df.columns):
        raise ValueError(
            f"El CSV debe contener al menos las columnas: {requeridas}\n"
            f"Columnas encontradas: {set(df.columns)}"
        )
    
    # Seleccionar y renombrar columnas para Prophet
    df_anual = df[["fecha", "total"]].copy()
    df_anual["fecha"] = pd.to_datetime(df_anual["fecha"])
    df_anual = df_anual.sort_values("fecha").dropna(subset=["fecha", "total"])
    
    return df_anual
