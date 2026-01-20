"""
test_model.py - Suite de pruebas unitarias para el modelo Prophet
==================================================================

Propósito:
- Validar la inicialización correcta del modelo
- Verificar que las predicciones se generan sin errores
- Comprobar que los escenarios climáticos se aplican correctamente
- Validar la clasificación de riesgo
- Probar el manejo de errores y casos límite

Casos de prueba esperados:
1. Importación del módulo sin errores
2. Modelo inicializado correctamente
3. Predicción básica con parámetros válidos
4. Comparación de escenarios (normal vs. seco)
5. Ajuste por nivel de usuario
6. Serialización a JSON
7. Manejo de errores (horizonte inválido, escenario desconocido, etc.)

Ejecución:
- Desde terminal: python test_model.py
- Debería mostrar X/X tests PASSED o detalles de fallos
"""

# Aquí irán las pruebas unitarias
# Se ejecutarán después de modificaciones en model.py para validar integridad


"""
test_model.py - Script de pruebas para el módulo model.py

Valida que el módulo carga correctamente y ejecuta el pipeline completo.
"""

import sys
from pathlib import Path

# Añadir el directorio al path para importar model
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

def test_importacion():
    """Test 1: Verificar que el módulo se importa correctamente"""
    print("\n" + "="*70)
    print("TEST 1: Importación del módulo")
    print("="*70)
    
    try:
        import model
        print("✓ Módulo importado exitosamente")
        print(f"✓ Función principal disponible: predecir_escenario")
        return True
    except Exception as e:
        print(f"✗ Error al importar: {e}")
        return False


def test_inicializacion():
    """Test 2: Verificar que el módulo se inicializa"""
    print("\n" + "="*70)
    print("TEST 2: Inicialización del módulo")
    print("="*70)
    
    try:
        import model
        
        if model.MODEL is None:
            print("✗ El modelo no se inicializó")
            return False
        
        if model.DF_ANUAL_PRED is None:
            print("✗ Los datos históricos no se cargaron")
            return False
        
        if model.DF_ESCENARIOS is None:
            print("✗ Los escenarios no se definieron")
            return False
        
        print(f"✓ Modelo Prophet: inicializado")
        print(f"✓ Datos históricos: {len(model.DF_ANUAL_PRED)} registros")
        print(f"✓ Escenarios: {len(model.DF_ESCENARIOS)}")
        print(f"✓ Umbrales:")
        print(f"  - Sequía severa (p10): {model.UMBRALES['umbral_sequia']:.2f} hm³")
        print(f"  - Nivel bajo (p25): {model.UMBRALES['umbral_bajo']:.2f} hm³")
        print(f"  - Último valor real: {model.Y_ULTIMO_REAL:.2f} hm³")
        
        return True
    
    except Exception as e:
        print(f"✗ Error en inicialización: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prediccion_basica():
    """Test 3: Generar una predicción básica"""
    print("\n" + "="*70)
    print("TEST 3: Predicción básica (escenario normal, sin ajuste)")
    print("="*70)
    
    try:
        import model
        
        respuesta = model.predecir_escenario(
            horizonte_meses=12,
            escenario="normal",
            nivel_actual_usuario=None
        )
        
        print(f"✓ Predicción generada")
        print(f"  - Escenario: {respuesta['escenario']}")
        print(f"  - Horizonte: {respuesta['horizonte_meses']} meses")
        print(f"  - Riesgo global: {respuesta['riesgo_global']}")
        print(f"  - Sequía probable: {respuesta['sequia_probable']}")
        print(f"  - Registros de predicción: {len(respuesta['prediccion_mensual'])}")
        
        # Mostrar primeros 3 meses
        print(f"\n  Primeros 3 meses:")
        for i, mes in enumerate(respuesta['prediccion_mensual'][:3]):
            print(f"    {i+1}. {mes['fecha']}: {mes['nivel']:.2f} hm³ ({mes['situacion']})")
        
        return True
    
    except Exception as e:
        print(f"✗ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_escenarios():
    """Test 4: Probar todos los escenarios"""
    print("\n" + "="*70)
    print("TEST 4: Comparativa de escenarios")
    print("="*70)
    
    try:
        import model
        
        escenarios = ["normal", "seco", "muy_seco", "humedo"]
        resultados = {}
        
        for esc in escenarios:
            respuesta = model.predecir_escenario(
                horizonte_meses=12,
                escenario=esc
            )
            
            nivel_promedio = sum(m['nivel'] for m in respuesta['prediccion_mensual']) / len(respuesta['prediccion_mensual'])
            meses_criticos = sum(1 for m in respuesta['prediccion_mensual'] if m['es_sequia'] or m['es_nivel_bajo'])
            
            resultados[esc] = {
                'riesgo': respuesta['riesgo_global'],
                'promedio': nivel_promedio,
                'criticos': meses_criticos
            }
            
            print(f"✓ {esc.upper():12} - Riesgo: {respuesta['riesgo_global']:10} | Promedio: {nivel_promedio:8.2f} hm³ | Meses críticos: {meses_criticos}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error comparando escenarios: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ajuste_usuario():
    """Test 5: Probar ajuste por nivel de usuario"""
    print("\n" + "="*70)
    print("TEST 5: Ajuste por nivel de usuario")
    print("="*70)
    
    try:
        import model
        
        # Predicción sin ajuste
        resp_sin = model.predecir_escenario(
            horizonte_meses=12,
            escenario="seco",
            nivel_actual_usuario=None
        )
        
        # Predicción con ajuste positivo
        nivel_alto = model.Y_ULTIMO_REAL + 20
        resp_alto = model.predecir_escenario(
            horizonte_meses=12,
            escenario="seco",
            nivel_actual_usuario=nivel_alto
        )
        
        # Predicción con ajuste negativo
        nivel_bajo = model.Y_ULTIMO_REAL - 15
        resp_bajo = model.predecir_escenario(
            horizonte_meses=12,
            escenario="seco",
            nivel_actual_usuario=nivel_bajo
        )
        
        nivel_sin = resp_sin['prediccion_mensual'][0]['nivel']
        nivel_con_alto = resp_alto['prediccion_mensual'][0]['nivel']
        nivel_con_bajo = resp_bajo['prediccion_mensual'][0]['nivel']
        
        delta_alto = nivel_con_alto - nivel_sin
        delta_bajo = nivel_con_bajo - nivel_sin
        
        print(f"✓ Última valor real: {model.Y_ULTIMO_REAL:.2f} hm³")
        print(f"\n  Nivel usuario: None")
        print(f"    Primer mes: {nivel_sin:.2f} hm³")
        
        print(f"\n  Nivel usuario: {nivel_alto:.2f} hm³ (+20)")
        print(f"    Primer mes: {nivel_con_alto:.2f} hm³")
        print(f"    Delta: {delta_alto:+.2f} hm³")
        
        print(f"\n  Nivel usuario: {nivel_bajo:.2f} hm³ (-15)")
        print(f"    Primer mes: {nivel_con_bajo:.2f} hm³")
        print(f"    Delta: {delta_bajo:+.2f} hm³")
        
        return True
    
    except Exception as e:
        print(f"✗ Error en ajuste por usuario: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_respuesta_json():
    """Test 6: Verificar que la respuesta es serializable a JSON"""
    print("\n" + "="*70)
    print("TEST 6: Serialización JSON")
    print("="*70)
    
    try:
        import json
        import model
        
        respuesta = model.predecir_escenario(
            horizonte_meses=6,
            escenario="seco",
            nivel_actual_usuario=810.0
        )
        
        # Intentar serializar a JSON
        json_str = json.dumps(respuesta, indent=2)
        
        print(f"✓ Respuesta es JSON-serializable")
        print(f"✓ Tamaño JSON: {len(json_str)} caracteres")
        print(f"\n  Primeras líneas del JSON:")
        
        lineas = json_str.split('\n')[:10]
        for linea in lineas:
            print(f"    {linea}")
        
        print(f"    ...")
        
        return True
    
    except Exception as e:
        print(f"✗ Error en serialización JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validacion_errores():
    """Test 7: Verificar manejo de errores"""
    print("\n" + "="*70)
    print("TEST 7: Validación de errores")
    print("="*70)
    
    try:
        import model
        
        # Test 7a: Escenario inválido
        try:
            model.predecir_escenario(escenario="invalido")
            print("✗ No se detectó escenario inválido")
            return False
        except ValueError:
            print("✓ Escenario inválido detectado correctamente")
        
        # Test 7b: Horizonte inválido (muy pequeño)
        try:
            model.predecir_escenario(horizonte_meses=0)
            print("✗ No se detectó horizonte inválido (< 1)")
            return False
        except ValueError:
            print("✓ Horizonte < 1 rechazado correctamente")
        
        # Test 7c: Horizonte inválido (muy grande)
        try:
            model.predecir_escenario(horizonte_meses=300)
            print("✗ No se detectó horizonte inválido (> 60)")
            return False
        except ValueError:
            print("✓ Horizonte > 60 rechazado correctamente")
        
        return True
    
    except Exception as e:
        print(f"✗ Error inesperado en validación: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "SUITE DE PRUEBAS: model.py" + " "*27 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("Importación del módulo", test_importacion),
        ("Inicialización del módulo", test_inicializacion),
        ("Predicción básica", test_prediccion_basica),
        ("Comparativa de escenarios", test_escenarios),
        ("Ajuste por nivel de usuario", test_ajuste_usuario),
        ("Serialización JSON", test_respuesta_json),
        ("Validación de errores", test_validacion_errores),
    ]
    
    resultados = []
    
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"\n✗ Test falló con excepción: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nombre, False))
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN DE PRUEBAS")
    print("="*70)
    
    exitosos = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        estado = "✓ PASÓ" if resultado else "✗ FALLÓ"
        print(f"{estado:10} - {nombre}")
    
    print("\n" + "="*70)
    print(f"RESULTADO: {exitosos}/{total} pruebas pasadas")
    print("="*70)
    
    if exitosos == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El módulo está listo para usar.\n")
        return 0
    else:
        print(f"\n⚠️  {total - exitosos} prueba(s) fallaron. Revisa los logs arriba.\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
