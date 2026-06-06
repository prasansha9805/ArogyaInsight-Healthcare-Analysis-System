
function esc(str) {
  if (str == null) return "—";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Return a coloured <span class="pill …"> for Recovery or Reaction values.
 */
function recoveryPill(value) {
  const v = (value || "").trim();
  if (v === "Fully Recovered")        return `<span class="pill pill-green">${esc(v)}</span>`;
  if (v === "Partially Recovered")    return `<span class="pill pill-amber">${esc(v)}</span>`;
  if (v === "Under Treatment")        return `<span class="pill pill-purple">${esc(v)}</span>`;
  return `<span class="pill pill-red">${esc(v)}</span>`;
}

function reactionPill(value) {
  const v = (value || "").trim();
  if (v === "No" || v === "None")     return `<span class="pill pill-green">${esc(v)}</span>`;
  if (v === "Mild")                   return `<span class="pill pill-amber">${esc(v)}</span>`;
  return `<span class="pill pill-red">${esc(v)}</span>`;
}

/**
 * Show / hide the inline spinner next to a button.
 */
function setLoading(spinnerId, active) {
  const el = document.getElementById(spinnerId);
  if (el) el.style.display = active ? "inline-block" : "none";
}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  SEGMENT 1 – Patient History Search  (part 1)                                     */
/* ══════════════════════════════════════════════════════════════════════════ */

async function searchPatient() {
  const input   = document.getElementById("patientQuery");
  const results = document.getElementById("patientResults");
  const query   = (input ? input.value : "").trim();

  if (!query) {
    results.innerHTML = `<p class="alert alert-info">Please enter a Patient ID or Name.</p>`;
    return;
  }

  setLoading("patientSpinner", true);
  results.innerHTML = "";

  try {
    const res  = await fetch(`/api/search-patient?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (!data.records || data.records.length === 0) {
      results.innerHTML = `<p class="alert alert-error">No records found for "<strong>${esc(query)}</strong>".</p>`;
      return;
    }

    // Build table
    const headers = ["Patient_ID","Name","Age","Gender","Disease",
                     "Medicine","Dosage","Reaction","Recovery","Visit_Date","Doctor"];

    const rows = data.records.map(r => `
      <tr>
        <td><span class="pill pill-purple" style="font-family:var(--font-mono)">${esc(r.Patient_ID)}</span></td>
        <td>${esc(r.Name)}</td>
        <td>${esc(r.Age)}</td>
        <td>${esc(r.Gender)}</td>
        <td>${esc(r.Disease)}</td>
        <td>${esc(r.Medicine)}</td>
        <td><code style="font-family:var(--font-mono);font-size:0.8rem">${esc(r.Dosage)}</code></td>
        <td>${reactionPill(r.Reaction)}</td>
        <td>${recoveryPill(r.Recovery)}</td>
        <td style="font-family:var(--font-mono);font-size:0.8rem">${esc(r.Visit_Date)}</td>
        <td>${esc(r.Doctor)}</td>
      </tr>
    `).join("");

    results.innerHTML = `
      <p style="font-size:0.82rem;color:var(--text-muted);margin-bottom:0.75rem;">
        Found <strong style="color:var(--teal)">${data.count}</strong> record(s) for "${esc(query)}"
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>${headers.map(h => `<th>${h.replace("_"," ")}</th>`).join("")}</tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (err) {
    results.innerHTML = `<p class="alert alert-error">Request failed: ${esc(err.message)}</p>`;
  } finally {
    setLoading("patientSpinner", false);
  }
}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  SEGMENT 2 – Medicine Efficiency                                            */
/* ══════════════════════════════════════════════════════════════════════════ */

async function searchMedicine() {
  const input    = document.getElementById("medicineQuery");
  const results  = document.getElementById("medicineResults");
  const chartBox = document.getElementById("medicineChart");
  const medicine = (input ? input.value : "").trim();

  if (!medicine) {
    results.innerHTML = `<p class="alert alert-info">Please enter a medicine name.</p>`;
    return;
  }

  setLoading("medicineSpinner", true);
  results.innerHTML = "";
  if (chartBox) chartBox.style.display = "none";

  try {
    const res  = await fetch(`/api/medicine-stats?medicine=${encodeURIComponent(medicine)}`);
    const data = await res.json();

    if (!data.found) {
      results.innerHTML = `<p class="alert alert-error">${esc(data.message)}</p>`;
      return;
    }

    const recoveryColor = data.recovery_rate >= 70 ? "var(--teal)"   : "var(--amber)";
    const reactionColor = data.reaction_rate >= 40 ? "var(--coral)"  : "var(--teal)";

    results.innerHTML = `
      <div class="stats-row">
        <div class="stat-chip">
          <span class="stat-val" style="color:var(--text-primary)">${data.total_prescribed}</span>
          <span class="stat-key">Times Prescribed</span>
        </div>
        <div class="stat-chip">
          <span class="stat-val" style="color:${recoveryColor}">${data.recovery_rate}%</span>
          <span class="stat-key">Recovery Rate</span>
        </div>
        <div class="stat-chip">
          <span class="stat-val" style="color:${reactionColor}">${data.reaction_rate}%</span>
          <span class="stat-key">Reaction Rate</span>
        </div>
      </div>
    `;

    // Force the browser to reload the newly generated chart
    if (chartBox) {
      const img = chartBox.querySelector("img");
      if (img) img.src = `/static/charts/medicine_chart.png?t=${Date.now()}`;
      chartBox.style.display = "block";
    }
  } catch (err) {
    results.innerHTML = `<p class="alert alert-error">Request failed: ${esc(err.message)}</p>`;
  } finally {
    setLoading("medicineSpinner", false);
  }
}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  search inputs                                       */
/* ══════════════════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  const patientInput  = document.getElementById("patientQuery");
  const medicineInput = document.getElementById("medicineQuery");

  if (patientInput) {
    patientInput.addEventListener("keydown", e => {
      if (e.key === "Enter") searchPatient();
    });
  }

  if (medicineInput) {
    medicineInput.addEventListener("keydown", e => {
      if (e.key === "Enter") searchMedicine();
    });
  }
});
