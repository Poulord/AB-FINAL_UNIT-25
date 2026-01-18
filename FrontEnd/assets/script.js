/*
script.js - Lógica del cliente JavaScript
===========================================

Propósito:
- Gestionar interacciones del usuario con el formulario
- Validar entrada en cliente antes de enviar al backend
- Comunicarse con la API de predicción (fetch POST)
- Renderizar resultados dinámicamente en el DOM
- Manejar errores y mostrar mensajes al usuario

Configuración global:
- BACKEND_URL: URL del servidor FastAPI (http://127.0.0.1:8000)
- LAST_DATA_DATE: Fecha de último dato histórico (2021-03-01)

Funciones principales:
- calcularMesesHastaFecha(fechaObjetivo, ultimaFecha)
  * Calcula meses entre dos fechas
  * Usado en modo B (fecha objetivo)
  
- form.addEventListener("submit", ...)
  * Captura envío del formulario
  * Valida datos
  * Construye payload JSON
  * Hace fetch al backend
  
- mostrarResultados(resultado)
  * Actualiza DOM con predicción
  * Aplica colores según riesgo
  * Rellena tabla con datos mensuales
  
- mostrarError(mensaje)
  * Muestra errores en interfaz
  * Limpia resultados previos

Modos de operación:
- Modo A: Horizonte manual (3, 6, 12, 24... meses)
- Modo B: Fecha objetivo (calcula meses automáticamente)

Dependencias externas:
- Fetch API (navegador nativo)
- DOM API (navegador nativo)
*/

// Configuración
// Detecta si estamos en local (abriendo el HTML en localhost)
const IS_LOCAL =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

// 👉 Pon aquí la URL pública de tu backend en Render/Railway
const BACKEND_URL = IS_LOCAL
  ? "http://127.0.0.1:8000"           // modo desarrollo local
  : "https://TU-BACKEND.onrender.com"; // modo producción (Vercel → Render)

// Última fecha de datos históricos del dataset
const LAST_DATA_DATE = "2021-03-01";


// Elementos del DOM
const form = document.getElementById("predictionForm");
const horizonte = document.getElementById("horizonte");
const escenario = document.getElementById("escenario");
const nivelUsuario = document.getElementById("nivelUsuario");
const fechaObjetivo = document.getElementById("fechaObjetivo");
const calcularBtn = document.getElementById("calcularBtn");
const resultsSection = document.getElementById("resultsSection");
const errorMessage = document.getElementById("errorMessage");
const riesgoBox = document.getElementById("riesgoBox");
const riesgoGlobal = document.getElementById("riesgoGlobal");
const sequiaInfo = document.getElementById("sequiaInfo");
const prediccionTbody = document.getElementById("prediccionTbody");

// Función para calcular meses entre dos fechas
function calcularMesesHastaFecha(fechaObjetivoISO, ultimaFechaISO) {
    const fechaObjetivoStr = fechaObjetivoISO.includes("-") && fechaObjetivoISO.length === 7 
        ? `${fechaObjetivoISO}-01` 
        : fechaObjetivoISO;
    
    const fechaObjetivo = new Date(fechaObjetivoStr + "T00:00:00Z");
    const ultimaFecha = new Date(ultimaFechaISO + "T00:00:00Z");

    if (isNaN(fechaObjetivo.getTime()) || isNaN(ultimaFecha.getTime())) {
        throw new Error("Las fechas no son válidas.");
    }

    if (fechaObjetivo <= ultimaFecha) {
        throw new Error(
            `La fecha objetivo (${fechaObjetivoISO}) debe ser posterior a la última fecha disponible (marzo 2021).`
        );
    }

    const años = fechaObjetivo.getFullYear() - ultimaFecha.getFullYear();
    const meses = fechaObjetivo.getMonth() - ultimaFecha.getMonth();
    const mesesTotales = años * 12 + meses;

    return mesesTotales;
}

// Event listener del formulario
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    calcularBtn.disabled = true;
    calcularBtn.textContent = "Calculando...";
    errorMessage.classList.remove("visible");
    resultsSection.classList.remove("visible");

    try {
        const escenarioValor = escenario.value;
        const nivelActual = nivelUsuario.value.trim() === "" ? null : parseFloat(nivelUsuario.value);

        let horizonteMeses;

        // MODO A: Usar fecha objetivo
        if (fechaObjetivo.value) {
            horizonteMeses = calcularMesesHastaFecha(fechaObjetivo.value, LAST_DATA_DATE);
        } 
        // MODO B: Usar número de meses manual
        else if (horizonte.value) {
            horizonteMeses = parseInt(horizonte.value, 10);
        }
        else {
            throw new Error("Por favor selecciona un horizonte de meses o una fecha objetivo.");
        }

        if (!escenarioValor) {
            throw new Error("Por favor selecciona un escenario climático.");
        }

        const payload = {
            horizonte_meses: horizonteMeses,
            escenario: escenarioValor,
            nivel_actual_usuario: nivelActual
        };

        const response = await fetch(`${BACKEND_URL}/predict`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Error en la predicción.");
        }

        const resultado = await response.json();
        mostrarResultados(resultado);

    } catch (error) {
        console.error("Error:", error);
        mostrarError(error.message);
    } finally {
        calcularBtn.disabled = false;
        calcularBtn.textContent = "Calcular riesgo de sequía";
    }
});

// Función para mostrar resultados
function mostrarResultados(resultado) {
    resultsSection.classList.add("visible");

    riesgoGlobal.textContent = resultado.riesgo_global;
    
    riesgoBox.className = "riesgo-box";
    const riesgoLower = resultado.riesgo_global.toLowerCase();
    riesgoBox.classList.add(riesgoLower);

    const sequiaMensaje = resultado.sequia_probable
        ? "⚠️ Sequía probable en el período"
        : "✓ Sin sequía probable en el período";
    sequiaInfo.textContent = sequiaMensaje;

    prediccionTbody.innerHTML = "";
    resultado.prediccion_mensual.forEach((mes) => {
        const fila = document.createElement("tr");

        let situacionClase = "situacion-normal";
        if (mes.es_sequia) {
            situacionClase = "situacion-sequia";
        } else if (mes.es_nivel_bajo) {
            situacionClase = "situacion-bajo";
        }

        const sequiaClase = mes.es_sequia ? "boolean-true" : "boolean-false";
        const bajoclase = mes.es_nivel_bajo ? "boolean-true" : "boolean-false";

        fila.innerHTML = `
            <td>${mes.fecha}</td>
            <td>${mes.nivel.toFixed(2)}</td>
            <td class="${situacionClase}">${mes.situacion}</td>
            <td class="${sequiaClase}">${mes.es_sequia ? "Sí" : "No"}</td>
            <td class="${bajoclase}">${mes.es_nivel_bajo ? "Sí" : "No"}</td>
        `;

        prediccionTbody.appendChild(fila);
    });
}

// Función para mostrar errores
function mostrarError(mensaje) {
    errorMessage.textContent = "❌ " + mensaje;
    errorMessage.classList.add("visible");
    resultsSection.classList.remove("visible");
    prediccionTbody.innerHTML = "";
}
