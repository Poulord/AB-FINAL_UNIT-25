/*
  script.js
  ---------------------------------------------------------------------------
  - Mantiene la lógica existente de predicción (POST /predict)
  - Añade navegación por pestañas (tabs) en una sola página
  - Añade status de API, copiar URL, reset y dashboard (último run)
*/

// -----------------------------
// Configuración
// -----------------------------
const IS_LOCAL =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

// 👉 Pon aquí la URL pública de tu backend en Render/Railway
const BACKEND_URL = IS_LOCAL
  ? "http://127.0.0.1:8000"               // modo desarrollo local
  : "https://backend-unit-25.onrender.com";    // modo producción (Vercel → Render)

// Última fecha de datos históricos del dataset
const LAST_DATA_DATE = "2021-03-01";

// -----------------------------
// Utilidades UI
// -----------------------------
function $(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function show(el) {
  if (!el) return;
  el.classList.add("visible");
}

function hide(el) {
  if (!el) return;
  el.classList.remove("visible");
}

function formatNow() {
  try {
    return new Intl.DateTimeFormat("es-ES", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date());
  } catch {
    return new Date().toLocaleString();
  }
}

// -----------------------------
// Tabs (pestañas)
// -----------------------------
function initTabs() {
  const tabButtons = Array.from(document.querySelectorAll(".tab[data-tab]"));
  const panels = Array.from(document.querySelectorAll(".tab-panel"));

  function activate(tabName) {
    tabButtons.forEach((btn) => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", String(isActive));
    });

    panels.forEach((p) => {
      const isActive = p.id === `tab-${tabName}`;
      p.classList.toggle("active", isActive);
    });
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => activate(btn.dataset.tab));
  });

  // Teclado (← →) en tablist
  const tablist = document.querySelector(".tabs[role='tablist']");
  if (tablist) {
    tablist.addEventListener("keydown", (e) => {
      const idx = tabButtons.findIndex((b) => b.classList.contains("active"));
      if (idx < 0) return;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = tabButtons[(idx + 1) % tabButtons.length];
        next.focus();
        next.click();
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prev = tabButtons[(idx - 1 + tabButtons.length) % tabButtons.length];
        prev.focus();
        prev.click();
      }
    });
  }
}

// -----------------------------
// API Status
// -----------------------------
async function checkApiStatus() {
  const pill = $("apiStatusPill");
  const dot = $("apiStatusDot");
  const text = $("apiStatusText");

  const set = (state, label) => {
    if (pill) {
      pill.classList.remove("ok", "warn", "bad");
      pill.classList.add(state);
    }
    if (dot) {
      dot.classList.remove("ok", "warn", "bad");
      dot.classList.add(state);
    }
    if (text) text.textContent = label;
  };

  // En el código original no había /health; aquí intentamos sin romper nada.
  // Si el backend NO tiene /health, hacemos fallback a un aviso “indeterminado”.
  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 2500);
    const res = await fetch(`${BACKEND_URL}/health`, { method: "GET", signal: controller.signal });
    clearTimeout(t);

    if (res.ok) set("ok", "API: OK");
    else set("warn", "API: responde (pero ojo)");
  } catch (e) {
    // Fallback: si no hay /health o hay CORS, al menos lo señalamos
    set("bad", "API: no disponible");
  }
}

function initCopyBackendUrl() {
  const btn = $("copyBackendUrl");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(BACKEND_URL);
      btn.textContent = "Copiado ✓";
      setTimeout(() => (btn.textContent = "Copiar URL"), 1200);
    } catch {
      // Fallback (corporativo): si clipboard falla, hacemos selección manual
      window.prompt("Copia la URL del backend:", BACKEND_URL);
    }
  });
}

// -----------------------------
// Predicción (lógica original)
// -----------------------------
const form = $("predictionForm");
const horizonte = $("horizonte");
const escenario = $("escenario");
const nivelUsuario = $("nivelUsuario");
const fechaObjetivo = $("fechaObjetivo");
const calcularBtn = $("calcularBtn");
const resetBtn = $("resetBtn");

const resultsSection = $("resultsSection");
const emptyState = $("emptyState");
const errorMessage = $("errorMessage");
const riesgoBox = $("riesgoBox");
const riesgoGlobal = $("riesgoGlobal");
const sequiaInfo = $("sequiaInfo");
const prediccionTbody = $("prediccionTbody");

function calcularMesesHastaFecha(fechaObjetivoISO, ultimaFechaISO) {
  const fechaObjetivoStr =
    fechaObjetivoISO.includes("-") && fechaObjetivoISO.length === 7
      ? `${fechaObjetivoISO}-01`
      : fechaObjetivoISO;

  const fechaObjetivoDate = new Date(fechaObjetivoStr + "T00:00:00Z");
  const ultimaFechaDate = new Date(ultimaFechaISO + "T00:00:00Z");

  if (isNaN(fechaObjetivoDate.getTime()) || isNaN(ultimaFechaDate.getTime())) {
    throw new Error("Las fechas no son válidas.");
  }

  if (fechaObjetivoDate <= ultimaFechaDate) {
    throw new Error(
      `La fecha objetivo (${fechaObjetivoISO}) debe ser posterior a la última fecha disponible (marzo 2021).`
    );
  }

  const años = fechaObjetivoDate.getFullYear() - ultimaFechaDate.getFullYear();
  const meses = fechaObjetivoDate.getMonth() - ultimaFechaDate.getMonth();
  return años * 12 + meses;
}

function setBusy(isBusy) {
  if (!calcularBtn) return;
  calcularBtn.disabled = isBusy;
  calcularBtn.textContent = isBusy ? "Calculando…" : "Calcular riesgo";
}

function mostrarResultados(resultado, meta = {}) {
  if (resultsSection) resultsSection.classList.add("visible");
  if (emptyState) emptyState.style.display = "none";

  if (riesgoGlobal) riesgoGlobal.textContent = resultado.riesgo_global;

  if (riesgoBox) {
    // reset clases
    riesgoBox.classList.remove("bajo", "moderado", "alto", "critico");
    const riesgoLower = String(resultado.riesgo_global || "").toLowerCase();
    if (["bajo", "moderado", "alto", "critico"].includes(riesgoLower)) {
      riesgoBox.classList.add(riesgoLower);
    }
  }

  const sequiaMensaje = resultado.sequia_probable
    ? "⚠️ Sequía probable en el período"
    : "✓ Sin sequía probable en el período";
  if (sequiaInfo) sequiaInfo.textContent = sequiaMensaje;

  if (prediccionTbody) {
    prediccionTbody.innerHTML = "";
    (resultado.prediccion_mensual || []).forEach((mes) => {
      const fila = document.createElement("tr");

      let situacionClase = "situacion-normal";
      if (mes.es_sequia) situacionClase = "situacion-sequia";
      else if (mes.es_nivel_bajo) situacionClase = "situacion-bajo";

      const sequiaClase = mes.es_sequia ? "boolean-true" : "boolean-false";
      const bajoClase = mes.es_nivel_bajo ? "boolean-true" : "boolean-false";

      fila.innerHTML = `
        <td>${mes.fecha}</td>
        <td>${Number(mes.nivel).toFixed(2)}</td>
        <td class="${situacionClase}">${mes.situacion}</td>
        <td class="${sequiaClase}">${mes.es_sequia ? "Sí" : "No"}</td>
        <td class="${bajoClase}">${mes.es_nivel_bajo ? "Sí" : "No"}</td>
      `;
      prediccionTbody.appendChild(fila);
    });
  }

  // Dashboard (último run)
  setText("dashLastRun", meta.timestamp || formatNow());
  setText("dashLastRisk", resultado.riesgo_global ?? "-");
  setText("dashLastHorizon", meta.horizonteMeses != null ? String(meta.horizonteMeses) : "-");
}

function mostrarError(mensaje) {
  if (!errorMessage) return;
  errorMessage.textContent = "❌ " + mensaje;
  errorMessage.classList.add("visible");

  if (resultsSection) resultsSection.classList.remove("visible");
  if (emptyState) emptyState.style.display = "flex";
  if (prediccionTbody) prediccionTbody.innerHTML = "";
}

function limpiarUI() {
  if (errorMessage) {
    errorMessage.classList.remove("visible");
    errorMessage.textContent = "";
  }
  if (resultsSection) resultsSection.classList.remove("visible");
  if (prediccionTbody) prediccionTbody.innerHTML = "";
  if (emptyState) emptyState.style.display = "flex";

  if (riesgoGlobal) riesgoGlobal.textContent = "-";
  if (sequiaInfo) sequiaInfo.textContent = "-";
  if (riesgoBox) riesgoBox.classList.remove("bajo", "moderado", "alto", "critico");

  // Dashboard
  setText("dashLastRun", "-");
  setText("dashLastRisk", "-");
  setText("dashLastHorizon", "-");
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    setBusy(true);
    if (errorMessage) errorMessage.classList.remove("visible");

    try {
      const escenarioValor = escenario?.value;
      const nivelActual = !nivelUsuario?.value?.trim() ? null : parseFloat(nivelUsuario.value);

      let horizonteMeses;

      // MODO A: Usar fecha objetivo
      if (fechaObjetivo?.value) {
        horizonteMeses = calcularMesesHastaFecha(fechaObjetivo.value, LAST_DATA_DATE);
      }
      // MODO B: Usar número de meses manual
      else if (horizonte?.value) {
        horizonteMeses = parseInt(horizonte.value, 10);
      } else {
        throw new Error("Por favor selecciona un horizonte de meses o una fecha objetivo.");
      }

      if (!escenarioValor) {
        throw new Error("Por favor selecciona un escenario climático.");
      }

      const payload = {
        horizonte_meses: horizonteMeses,
        escenario: escenarioValor,
        nivel_actual_usuario: nivelActual,
      };

      const response = await fetch(`${BACKEND_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = "Error en la predicción.";
        try {
          const errorData = await response.json();
          detail = errorData.detail || detail;
        } catch {
          // ignore parse errors
        }
        throw new Error(detail);
      }

      const resultado = await response.json();
      mostrarResultados(resultado, { horizonteMeses, timestamp: formatNow() });

      // Si la API estaba “mal”, re-chequeamos (por si solo era /health ausente/CORS)
      checkApiStatus();

    } catch (error) {
      console.error("Error:", error);
      mostrarError(error?.message || "Error inesperado.");
    } finally {
      setBusy(false);
    }
  });
}

if (resetBtn) {
  resetBtn.addEventListener("click", () => {
    if (form) form.reset();
    limpiarUI();
  });
}

// -----------------------------
// Init
// -----------------------------
(function init() {
  initTabs();
  initCopyBackendUrl();

  setText("backendUrlDisplay", BACKEND_URL);
  setText("lastDataDisplay", LAST_DATA_DATE);
  setText("dashBackend", BACKEND_URL);
  setText("dashLastData", LAST_DATA_DATE);
  setText("yearNow", String(new Date().getFullYear()));

  // Estado inicial
  if (emptyState) emptyState.style.display = "flex";
  limpiarUI();

  // Comprobación API
  checkApiStatus();
})();
