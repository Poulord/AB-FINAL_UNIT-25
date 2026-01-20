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


def calcular_umbrales(serie_y: pd.Series) -> Dict[str, float]:
    """
    Calcula umbrales de riesgo basados en percentiles de la serie histórica.
    
    Parámetros
    ----------
    serie_y : pd.Series
        Serie de volúmenes históricos
    
    Retorna
    -------
    dict
        Diccionario con claves:
        - 'umbral_bajo': percentil 25 (nivel bajo)
        - 'umbral_sequia': percentil 10 (sequía severa)
        - 'media': media histórica
    """
    return {
        'umbral_bajo': np.percentile(serie_y, 25),
        'umbral_sequia': np.percentile(serie_y, 10),
        'media': float(serie_y.mean())
    }


def entrenar_modelo(df_anual: pd.DataFrame) -> Tuple[Prophet, float]:
    """
    Entrena un modelo Prophet con datos históricos.
    
    Parámetros
    ----------
    df_anual : pd.DataFrame
        DataFrame con columnas 'fecha' y 'total'
    
    Retorna
    -------
    tuple
        (modelo Prophet entrenado, último valor real observado)
    """
    # Preparar datos en formato Prophet (ds, y)
    df_prophet = df_anual.rename(columns={"fecha": "ds", "total": "y"}).copy()
    
    # Entrenar modelo
    modelo = Prophet()
    modelo.fit(df_prophet)
    
    y_ultimo = df_prophet["y"].iloc[-1]
    
    return modelo, y_ultimo


def inicializar_modulo(ruta_csv: Optional[str] = None) -> None:
    """
    Inicializa el módulo: carga datos, entrena Prophet, define escenarios.
    
    Se ejecuta automáticamente al importar el módulo.
    
    Parámetros
    ----------
    ruta_csv : str, optional
        Ruta al CSV de embalses limpios. Si es None, usa DATA_FILE
    
    Raises
    ------
    FileNotFoundError
        Si no se encuentra el archivo de datos
    ValueError
        Si hay errores en la estructura de datos
    """
    global MODEL, DF_ANUAL_PRED, DF_ESCENARIOS, UMBRALES, Y_ULTIMO_REAL
    
    if ruta_csv is None:
        ruta_csv = str(DATA_FILE)
    
    print(f"[INFO] Inicializando módulo de predicción...")
    print(f"[INFO] Cargando datos desde: {ruta_csv}")
    
    # 1. Cargar datos históricos
    df_anual = cargar_datos_historicos(ruta_csv)
    print(f"[INFO] Datos históricos cargados: {len(df_anual)} registros")
    
    # 2. Preparar DataFrame para Prophet
    DF_ANUAL_PRED = df_anual.rename(columns={"fecha": "ds", "total": "y"}).copy()
    
    # 3. Calcular umbrales
    UMBRALES = calcular_umbrales(DF_ANUAL_PRED["y"])
    Y_ULTIMO_REAL = DF_ANUAL_PRED["y"].iloc[-1]
    print(f"[INFO] Umbrales calculados:")
    print(f"       - Sequía severa (p10): {UMBRALES['umbral_sequia']:.2f} hm³")
    print(f"       - Nivel bajo (p25): {UMBRALES['umbral_bajo']:.2f} hm³")
    print(f"       - Último valor real: {Y_ULTIMO_REAL:.2f} hm³")
    
    # 4. Entrenar Prophet
    MODEL, Y_ULTIMO_REAL = entrenar_modelo(DF_ANUAL_PRED)
    print(f"[INFO] Modelo Prophet entrenado exitosamente")
    
    # 5. Definir escenarios climáticos
    DF_ESCENARIOS = pd.DataFrame({
        'escenario': ['normal', 'seco', 'muy_seco', 'humedo'],
        'factor_volumen': [1.0, 0.9, 0.8, 1.1],
        'descripcion': [
            'Condiciones normales de precipitación',
            'Condiciones secas (reducción 10%)',
            'Sequía severa (reducción 20%)',
            'Condiciones húmedas (aumento 10%)'
        ]
    })
    print(f"[INFO] Escenarios climáticos definidos: {len(DF_ESCENARIOS)}")
    print("[INFO] Módulo inicializado correctamente ✓")


# ============================================================================
# FUNCIONES PURAS DE PROCESAMIENTO
# ============================================================================

def validar_escenario(escenario: str) -> bool:
    """
    Valida si un escenario existe en la lista de escenarios definidos.
    
    Parámetros
    ----------
    escenario : str
        Nombre del escenario a validar
    
    Retorna
    -------
    bool
        True si el escenario es válido
    
    Raises
    ------
    ValueError
        Si el escenario no existe
    """
    if DF_ESCENARIOS is None:
        raise RuntimeError("Módulo no inicializado. Llama a inicializar_modulo() primero.")
    
    escenarios_validos = DF_ESCENARIOS['escenario'].tolist()
    
    if escenario not in escenarios_validos:
        raise ValueError(
            f"Escenario '{escenario}' no existe.\n"
            f"Opciones válidas: {escenarios_validos}"
        )
    
    return True


def generar_forecast_base(horizonte_meses: int) -> pd.DataFrame:
    """
    Genera el forecast base (sin ajustes) usando Prophet.
    
    Parámetros
    ----------
    horizonte_meses : int
        Número de meses futuros a predecir (típicamente 12)
    
    Retorna
    -------
    pd.DataFrame
        DataFrame con columnas:
        - ds: fecha
        - yhat: predicción central
        - yhat_lower: intervalo inferior
        - yhat_upper: intervalo superior
    
    Raises
    ------
    RuntimeError
        Si el módulo no está inicializado
    """
    if MODEL is None or DF_ANUAL_PRED is None:
        raise RuntimeError("Módulo no inicializado. Llama a inicializar_modulo() primero.")
    
    # Crear fechas futuras
    ultima_fecha = DF_ANUAL_PRED["ds"].max()
    future = MODEL.make_future_dataframe(periods=horizonte_meses, freq="MS")
    
    # Generar predicciones
    forecast = MODEL.predict(future)
    
    # Retornar solo los próximos horizonte_meses
    forecast_futuro = forecast[forecast["ds"] > ultima_fecha][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].head(horizonte_meses).copy()
    
    return forecast_futuro


def aplicar_escenario(pred_df: pd.DataFrame, escenario: str) -> pd.DataFrame:
    """
    Aplica un escenario climático a las predicciones.
    
    Parámetros
    ----------
    pred_df : pd.DataFrame
        DataFrame con predicciones base (columnas: ds, yhat, yhat_lower, yhat_upper)
    escenario : str
        Nombre del escenario ('normal', 'seco', 'muy_seco', 'humedo')
    
    Retorna
    -------
    pd.DataFrame
        Copia de pred_df con columnas adicionales:
        - yhat_adj: predicción ajustada
        - yhat_lower_adj: intervalo inferior ajustado
        - yhat_upper_adj: intervalo superior ajustado
    
    Raises
    ------
    ValueError
        Si el escenario no existe
    """
    # Validar escenario
    validar_escenario(escenario)
    
    # Obtener factor del escenario
    factor = DF_ESCENARIOS[
        DF_ESCENARIOS['escenario'] == escenario
    ]['factor_volumen'].values[0]
    
    # Aplicar factor
    resultado = pred_df.copy()
    resultado['yhat_adj'] = resultado['yhat'] * factor
    resultado['yhat_lower_adj'] = resultado['yhat_lower'] * factor
    resultado['yhat_upper_adj'] = resultado['yhat_upper'] * factor
    
    return resultado


def ajustar_por_nivel_usuario(
    pred_df: pd.DataFrame,
    y_ultimo_real: float,
    nivel_actual_usuario: Optional[float] = None
) -> pd.DataFrame:
    """
    Ajusta las predicciones según el nivel actual del embalse reportado por usuario.
    
    Calcula delta = (nivel_actual_usuario - y_ultimo_real) y lo suma a las
    predicciones ajustadas para reflejar un punto de partida diferente.
    
    Parámetros
    ----------
    pred_df : pd.DataFrame
        DataFrame con predicciones ajustadas (columnas: yhat_adj, yhat_lower_adj, yhat_upper_adj)
    y_ultimo_real : float
        Último valor real observado en datos históricos
    nivel_actual_usuario : float, optional
        Nivel actual reportado por el usuario. Si None, no aplica ajuste adicional.
    
    Retorna
    -------
    pd.DataFrame
        Copia de pred_df con columnas adicionales:
        - yhat_final: predicción central calibrada
        - yhat_lower_final: intervalo inferior calibrado
        - yhat_upper_final: intervalo superior calibrado
    
    Ejemplo
    -------
    >>> forecast_ajustado = ajustar_por_nivel_usuario(
    ...     pred_df=forecast_escenario,
    ...     y_ultimo_real=650.5,
    ...     nivel_actual_usuario=660.0
    ... )
    # delta = 660.0 - 650.5 = 9.5
    # yhat_final = yhat_adj + 9.5
    """
    resultado = pred_df.copy()
    
    # Calcular delta
    if nivel_actual_usuario is None:
        delta = 0.0
    else:
        delta = nivel_actual_usuario - y_ultimo_real
    
    # Crear columnas finales
    resultado['yhat_final'] = resultado['yhat_adj'] + delta
    resultado['yhat_lower_final'] = resultado['yhat_lower_adj'] + delta
    resultado['yhat_upper_final'] = resultado['yhat_upper_adj'] + delta
    
    return resultado


def clasificar_riesgo(
    pred_df: pd.DataFrame,
    umbral_bajo: float,
    umbral_sequia: float
) -> Tuple[pd.DataFrame, str]:
    """
    Clasifica el riesgo de sequía por mes y calcula un riesgo global.
    
    Parámetros
    ----------
    pred_df : pd.DataFrame
        DataFrame con predicciones calibradas (columna: yhat_final)
    umbral_bajo : float
        Umbral para "nivel bajo" (típicamente percentil 25)
    umbral_sequia : float
        Umbral para "sequía severa" (típicamente percentil 10)
    
    Retorna
    -------
    tuple
        (DataFrame con clasificaciones, riesgo_global como string)
    
    El DataFrame contiene columnas adicionales:
        - es_sequia (bool): True si yhat_final < umbral_sequia
        - es_bajo (bool): True si umbral_sequia <= yhat_final < umbral_bajo
        - situacion (str): "Sequía severa", "Nivel bajo", "Normal"
    
    El riesgo_global es uno de:
        - "CRÍTICO": > 50% de meses en situación crítica
        - "ALTO": 30-50% de meses
        - "MODERADO": 10-30% de meses
        - "BAJO": < 10% de meses
    """
    resultado = pred_df.copy()
    
    # Clasificaciones por mes
    resultado['es_sequia'] = resultado['yhat_final'] < umbral_sequia
    resultado['es_bajo'] = (
        (resultado['yhat_final'] >= umbral_sequia) &
        (resultado['yhat_final'] < umbral_bajo)
    )
    
    def asignar_situacion(row):
        if row['es_sequia']:
            return 'Sequía severa'
        elif row['es_bajo']:
            return 'Nivel bajo'
        else:
            return 'Normal'
    
    resultado['situacion'] = resultado.apply(asignar_situacion, axis=1)
    
    # Calcular riesgo global
    total_meses = len(resultado)
    meses_criticos = (resultado['es_sequia'] | resultado['es_bajo']).sum()
    porcentaje = (meses_criticos / total_meses * 100) if total_meses > 0 else 0
    
    if porcentaje > 50:
        riesgo_global = "CRÍTICO"
    elif porcentaje > 30:
        riesgo_global = "ALTO"
    elif porcentaje > 10:
        riesgo_global = "MODERADO"
    else:
        riesgo_global = "BAJO"
    
    return resultado, riesgo_global


def construir_respuesta_api(
    escenario: str,
    horizonte_meses: int,
    nivel_actual_usuario: Optional[float],
    pred_df: pd.DataFrame,
    riesgo_global: str
) -> Dict[str, Any]:
    """
    Construye una respuesta JSON-serializable con predicciones y análisis de riesgo.
    
    Parámetros
    ----------
    escenario : str
        Escenario climático aplicado
    horizonte_meses : int
        Número de meses predichos
    nivel_actual_usuario : float or None
        Nivel reportado por el usuario (None si sin ajuste)
    pred_df : pd.DataFrame
        DataFrame con predicciones clasificadas
    riesgo_global : str
        Clasificación de riesgo global
    
    Retorna
    -------
    dict
        Estructura JSON-serializable con:
        
        {
            "escenario": str,
            "horizonte_meses": int,
            "nivel_actual_usuario": float or None,
            "riesgo_global": str,
            "sequia_probable": bool,
            "prediccion_mensual": [
                {
                    "fecha": str (YYYY-MM-DD),
                    "nivel": float,
                    "situacion": str,
                    "es_sequia": bool,
                    "es_nivel_bajo": bool
                },
                ...
            ]
        }
    """
    # Determinar si hay sequía probable
    sequia_probable = riesgo_global in ["ALTO", "CRÍTICO"]
    
    # Construir predicciones mensuales
    prediccion_mensual = []
    for _, row in pred_df.head(horizonte_meses).iterrows():
        prediccion_mensual.append({
            "fecha": row['ds'].strftime('%Y-%m-%d'),
            "nivel": round(float(row['yhat_final']), 2),
            "situacion": str(row['situacion']),
            "es_sequia": bool(row['es_sequia']),
            "es_nivel_bajo": bool(row['es_bajo'])
        })
    
    # Respuesta completa
    respuesta = {
        "escenario": escenario,
        "horizonte_meses": horizonte_meses,
        "nivel_actual_usuario": float(nivel_actual_usuario) if nivel_actual_usuario is not None else None,
        "riesgo_global": riesgo_global,
        "sequia_probable": sequia_probable,
        "prediccion_mensual": prediccion_mensual
    }
    
    return respuesta


# ============================================================================
# FUNCIÓN PRINCIPAL DE ALTO NIVEL (INTERFAZ CON FASTAPI)
# ============================================================================

def predecir_escenario(
    horizonte_meses: int = 12,
    escenario: str = "normal",
    nivel_actual_usuario: Optional[float] = None
) -> Dict[str, Any]:
    """
    Función principal que implementa el pipeline completo de predicción.
    
    Esta es la ÚNICA función que debe consumir el backend FastAPI.
    
    Parámetros
    ----------
    horizonte_meses : int, default=12
        Número de meses a predecir
    escenario : str, default="normal"
        Escenario climático: 'normal', 'seco', 'muy_seco', 'humedo'
    nivel_actual_usuario : float, optional
        Nivel actual del embalse reportado por usuario.
        Si None, usa el último valor histórico sin ajuste.
    
    Retorna
    -------
    dict
        Respuesta JSON-serializable con estructura de predicción
    
    Raises
    ------
    RuntimeError
        Si el módulo no está inicializado
    ValueError
        Si el escenario no existe o parámetros son inválidos
    
    Ejemplo
    -------
    >>> respuesta = predecir_escenario(
    ...     horizonte_meses=12,
    ...     escenario='seco',
    ...     nivel_actual_usuario=810.0
    ... )
    >>> print(respuesta['riesgo_global'])
    'MODERADO'
    """
    # Validación de módulo inicializado
    if MODEL is None or DF_ANUAL_PRED is None:
        raise RuntimeError(
            "Módulo no inicializado. Llama a inicializar_modulo() primero."
        )
    
    # Validación de escenario
    validar_escenario(escenario)
    
    # Validación de parámetros
    if horizonte_meses < 1 or horizonte_meses > 180:
        raise ValueError(
            f"horizonte_meses debe estar entre 1 y 180. Recibido: {horizonte_meses}"
        )
    
    # Pipeline completo
    # 1. Generar forecast base
    forecast = generar_forecast_base(horizonte_meses)
    
    # 2. Aplicar escenario
    forecast = aplicar_escenario(forecast, escenario)
    
    # 3. Ajustar por nivel de usuario
    forecast = ajustar_por_nivel_usuario(
        forecast,
        y_ultimo_real=Y_ULTIMO_REAL,
        nivel_actual_usuario=nivel_actual_usuario
    )
    
    # 4. Clasificar riesgo
    forecast, riesgo_global = clasificar_riesgo(
        forecast,
        umbral_bajo=UMBRALES['umbral_bajo'],
        umbral_sequia=UMBRALES['umbral_sequia']
    )
    
    # 5. Construir respuesta API
    respuesta = construir_respuesta_api(
        escenario=escenario,
        horizonte_meses=horizonte_meses,
        nivel_actual_usuario=nivel_actual_usuario,
        pred_df=forecast,
        riesgo_global=riesgo_global
    )
    
    return respuesta


# ============================================================================
# INICIALIZACIÓN AUTOMÁTICA AL IMPORTAR
# ============================================================================

# TODO: Si quieres cambiar la ruta del CSV, pasa el path aquí
try:
    inicializar_modulo()
except Exception as e:
    print(f"[ERROR] No se pudo inicializar el módulo: {e}")
    print(f"[ERROR] Verifica que exista el archivo en: {DATA_FILE}")
