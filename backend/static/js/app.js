// MediSync Frontend Application Script

let currentReport = null;
let currentDoctorReport = null;
let doctorsList = [];
let html5QrScanner = null;
let isScannerActive = false;
let speechRecognition = null;
let isRecordingVoice = false;
let lastVoiceTextResponse = "";

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initHumanInteractionTracking();
  loadDoctors();
  loadRecentReportsList();
  initVoiceRecognition();

  // Check URL params for direct doctor access
  const params = new URLSearchParams(window.location.search);
  if (params.get("portal") === "doctor") {
    switchPortal("doctor");
    if (params.get("token")) {
      document.getElementById("doctor-token-input").value = params.get("token");
      lookupPatientReport();
    }
  }

  // Setup drag and drop
  setupDragAndDrop();
});

// Anti-Bot Human Interaction Tracker
let isHumanActivityDetected = false;
function initHumanInteractionTracking() {
  const markHuman = () => {
    isHumanActivityDetected = true;
    window.removeEventListener("mousemove", markHuman);
    window.removeEventListener("touchstart", markHuman);
    window.removeEventListener("keydown", markHuman);
  };
  window.addEventListener("mousemove", markHuman, { once: true });
  window.addEventListener("touchstart", markHuman, { once: true });
  window.addEventListener("keydown", markHuman, { once: true });
}

// Portal Switching
function switchPortal(portal) {
  const patientView = document.getElementById("patient-portal-view");
  const doctorView = document.getElementById("doctor-portal-view");
  const btnPatient = document.getElementById("btn-patient-portal");
  const btnDoctor = document.getElementById("btn-doctor-portal");

  if (portal === "patient") {
    patientView.style.display = "block";
    doctorView.style.display = "none";
    btnPatient.classList.add("active");
    btnDoctor.classList.remove("active");
  } else {
    patientView.style.display = "none";
    doctorView.style.display = "block";
    btnPatient.classList.remove("active");
    btnDoctor.classList.add("active");
    loadDoctorAppointments();
    loadRecentReportsList();
  }
}

// Subtab Switching (Patient)
function switchPatientTab(tabId) {
  const tabs = ["analyze", "kb", "book", "my-appts", "voice"];
  tabs.forEach(t => {
    const el = document.getElementById(`patient-tab-${t}`);
    if (el) el.style.display = (t === tabId) ? "block" : "none";
  });

  const links = document.querySelectorAll("#patient-portal-view .tab-link");
  links.forEach((l, idx) => {
    l.classList.toggle("active", tabs[idx] === tabId);
  });

  if (tabId === "my-appts") {
    loadPatientAppointments();
  } else if (tabId === "kb") {
    loadMedicalKnowledgeBase();
  }
}

// Subtab Switching (Doctor)
function switchDoctorTab(tabId) {
  const tabs = ["scan", "schedule"];
  tabs.forEach(t => {
    const el = document.getElementById(`doctor-tab-${t}`);
    if (el) el.style.display = (t === tabId) ? "block" : "none";
  });

  const links = document.querySelectorAll("#doctor-portal-view .tab-link");
  links.forEach((l, idx) => {
    l.classList.toggle("active", tabs[idx] === tabId);
  });

  if (tabId === "schedule") {
    loadDoctorAppointments();
  }
}

// Drag & Drop Setup
function setupDragAndDrop() {
  const dropZone = document.getElementById("drop-zone");
  if (!dropZone) return;

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });
}

function handleFileSelected(event) {
  const files = event.target.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
}

let activeUploadedFile = null;
function handleFile(file) {
  activeUploadedFile = file;
  document.getElementById("selected-filename").innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  document.getElementById("selected-file-info").style.display = "flex";
}

// Upload & Analyze Report
async function uploadAndAnalyze() {
  if (!activeUploadedFile) return;

  const formData = new FormData();
  formData.append("file", activeUploadedFile);
  formData.append("patient_name", "Sarah Connor");

  // Anti-bot honeypot check
  const botTrapEl = document.getElementById("upload-bot-trap");
  if (botTrapEl && botTrapEl.value) {
    formData.append("bot_trap", botTrapEl.value);
  }

  showLoader(true);

  try {
    const response = await fetch("/api/analyze-report", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    showLoader(false);

    if (data.success) {
      renderAnalysis(data.record);
    } else {
      alert("Analysis failed: " + (data.detail || "Unknown error"));
    }
  } catch (error) {
    showLoader(false);
    alert("Connection error while analyzing report: " + error.message);
  }
}

// Quick Sample Report Loader
async function loadSampleReport(type) {
  showLoader(true);
  try {
    const response = await fetch(`/api/sample-report?sample_type=${type}&patient_name=Sarah%20Connor`, {
      method: "POST"
    });
    const data = await response.json();
    showLoader(false);

    if (data.success) {
      renderAnalysis(data.record);
    }
  } catch (error) {
    showLoader(false);
    alert("Error loading sample report: " + error.message);
  }
}

function showLoader(visible) {
  document.getElementById("analysis-loader").style.display = visible ? "block" : "none";
  if (visible) {
    document.getElementById("analysis-placeholder").style.display = "none";
    document.getElementById("analysis-results-container").style.display = "none";
  }
}

// Render Analysis in Patient Portal
function renderAnalysis(record) {
  currentReport = record;
  const analysis = record.analysis;

  document.getElementById("analysis-placeholder").style.display = "none";
  document.getElementById("analysis-results-container").style.display = "block";

  // Disclaimer
  document.getElementById("analysis-disclaimer-text").innerText = 
    analysis.disclaimer || "CRITICAL: This AI analysis is purely educational and descriptive. It does NOT provide medical diagnosis or conclude diseases. Consult your doctor.";

  // Title & Metadata
  document.getElementById("report-title-display").innerText = analysis.report_title || "Laboratory Report";
  document.getElementById("report-meta-display").innerText = `Patient: ${record.patient_name} • Specimen: ${analysis.sample_date_detected || "Analyzed"} • Token: ${record.token}`;
  document.getElementById("report-overview-text").innerText = analysis.summary_overview || "Detailed laboratory summary.";

  // AI Engine Badge
  const engineBadge = document.getElementById("ai-engine-badge");
  if (engineBadge) {
    engineBadge.innerText = analysis.ai_engine || "MedGemma RAG";
  }

  // Parameters Table
  const tbody = document.getElementById("param-table-body");
  tbody.innerHTML = "";

  (analysis.parameters || []).forEach(p => {
    const tr = document.createElement("tr");

    let badgeClass = "badge-normal";
    const statusLower = (p.status || "").toLowerCase();
    if (statusLower.includes("high") || statusLower.includes("elevated")) badgeClass = "badge-high";
    else if (statusLower.includes("low") || statusLower.includes("decreased")) badgeClass = "badge-low";
    else if (statusLower.includes("borderline")) badgeClass = "badge-borderline";

    const limitationsHtml = p.biological_limitations ? 
      `<div style="font-size: 0.76rem; color: #b45309; margin-top: 3px;">⚠️ <em>Pre-analytical variation: ${p.biological_limitations}</em></div>` : "";

    tr.innerHTML = `
      <td>
        <div class="param-name">${p.name}</div>
        <div class="param-desc">${p.explanation || ""}</div>
        ${limitationsHtml}
      </td>
      <td><strong>${p.value}</strong></td>
      <td style="color: var(--gray-600);">${p.reference_range || "N/A"}</td>
      <td><span class="badge ${badgeClass}">${p.status || "Normal"}</span></td>
    `;
    tbody.appendChild(tr);
  });

  // Observations
  const obsList = document.getElementById("general-obs-list");
  obsList.innerHTML = "";
  (analysis.general_observations || []).forEach(obs => {
    const li = document.createElement("li");
    li.innerText = obs;
    obsList.appendChild(li);
  });

  // Questions for doctor
  const qList = document.getElementById("doctor-questions-list");
  qList.innerHTML = "";
  (analysis.questions_for_doctor || []).forEach(q => {
    const li = document.createElement("li");
    li.innerText = q;
    qList.appendChild(li);
  });

  // Reference Range Limitations Guide
  const limList = document.getElementById("reference-limitations-list");
  if (limList) {
    limList.innerHTML = "";
    const limitations = analysis.reference_range_limitations || [];
    if (limitations.length === 0) {
      limList.innerHTML = `<li>Reference intervals represent a 95% statistical confidence interval of a healthy population; single slight deviations are common and non-diagnostic.</li>`;
    } else {
      limitations.forEach(lim => {
        const li = document.createElement("li");
        li.innerText = lim;
        limList.appendChild(li);
      });
    }
  }

  // Authoritative Sources Cited
  const sourcesContainer = document.getElementById("sources-cited-badges");
  if (sourcesContainer) {
    sourcesContainer.innerHTML = "";
    const sources = analysis.authoritative_sources || [];
    sources.forEach(s => {
      const span = document.createElement("a");
      span.href = s.url || "#";
      span.target = "_blank";
      span.className = "chip-btn";
      span.style.fontSize = "0.72rem";
      span.style.textDecoration = "none";
      span.innerText = `📖 ${s.organization || s.resource || s}`;
      sourcesContainer.appendChild(span);
    });
  }

  // QR Code Pass
  const qrCard = document.getElementById("qr-access-card");
  const qrImg = document.getElementById("qr-code-image");
  const qrTokenText = document.getElementById("qr-token-text");

  qrImg.src = `/api/qr/${record.token}?t=${Date.now()}`;
  qrTokenText.innerText = record.token;
  qrCard.style.display = "block";

  // Pre-fill appointment token
  document.getElementById("appt-report-token").value = record.token;
  document.getElementById("appt-patient-name").value = record.patient_name || "";

  // Update RAG Chatbot active report badge
  const chatBadge = document.getElementById("chat-active-report-badge");
  if (chatBadge) {
    chatBadge.innerText = `📄 Active: ${record.patient_name || 'Patient'} (${record.token})`;
    chatBadge.classList.add("active");
  }
}

function copyToken() {
  if (!currentReport) return;
  navigator.clipboard.writeText(currentReport.token);
  alert(`Report Access Token ${currentReport.token} copied to clipboard!`);
}

function openDoctorDirect() {
  if (!currentReport) return;
  switchPortal("doctor");
  document.getElementById("doctor-token-input").value = currentReport.token;
  lookupPatientReport();
}

function proceedToBookingWithCurrentReport() {
  switchPatientTab("book");
  if (currentReport) {
    document.getElementById("appt-report-token").value = currentReport.token;
    document.getElementById("appt-patient-name").value = currentReport.patient_name;
  }
}

// Doctors & Appointments
async function loadDoctors() {
  try {
    const response = await fetch("/api/doctors");
    doctorsList = await response.json();

    const grid = document.getElementById("doctor-select-grid");
    if (!grid) return;
    grid.innerHTML = "";

    doctorsList.forEach((doc, idx) => {
      const card = document.createElement("div");
      card.className = `doctor-card-select ${idx === 0 ? "selected" : ""}`;
      card.onclick = () => selectDoctor(doc.id, card);
      card.innerHTML = `
        <div class="doc-avatar">${doc.avatar || "👨‍⚕️"}</div>
        <div>
          <strong style="font-size: 0.92rem; display: block;">${doc.name}</strong>
          <span style="font-size: 0.78rem; color: var(--primary); font-weight: 600;">${doc.specialty}</span>
          <span style="font-size: 0.75rem; color: var(--gray-500); display: block;">${doc.hospital}</span>
        </div>
      `;
      grid.appendChild(card);
    });

    if (doctorsList.length > 0) {
      document.getElementById("selected-doctor-id").value = doctorsList[0].id;
    }
  } catch (e) {
    console.error("Failed to load doctors:", e);
  }
}

function selectDoctor(docId, cardElement) {
  document.querySelectorAll(".doctor-card-select").forEach(c => c.classList.remove("selected"));
  cardElement.classList.add("selected");
  document.getElementById("selected-doctor-id").value = docId;
}

async function handleAppointmentSubmit(event) {
  event.preventDefault();

  const patient_name = document.getElementById("appt-patient-name").value;
  const patient_phone = document.getElementById("appt-patient-phone").value;
  const doctor_id = document.getElementById("selected-doctor-id").value;
  const date = document.getElementById("appt-date").value;
  const time = document.getElementById("appt-time").value;
  const report_token = document.getElementById("appt-report-token").value;
  const reason = document.getElementById("appt-reason").value;

  // Anti-bot honeypot check
  const botTrapEl = document.getElementById("appt-bot-trap");
  const bot_trap = botTrapEl && botTrapEl.value ? botTrapEl.value : null;

  try {
    const response = await fetch("/api/appointments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name,
        patient_phone,
        doctor_id,
        date,
        time,
        reason: reason || "General Consultation",
        report_token: report_token || null,
        bot_trap: bot_trap
      })
    });

    const data = await response.json();
    alert(`Appointment Confirmed with ${data.appointment.doctor_name} for ${date} at ${time}!`);
    switchPatientTab("my-appts");
  } catch (error) {
    alert("Error scheduling appointment: " + error.message);
  }
}

async function loadPatientAppointments() {
  try {
    const res = await fetch("/api/appointments");
    const appts = await res.json();

    const container = document.getElementById("patient-appts-list");
    if (!container) return;

    if (appts.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; color: var(--gray-500);">
          <p>No appointments booked yet. Click 'Book Appointment' to schedule one.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = appts.map(a => `
      <div style="padding: 1rem; border: 1px solid var(--gray-200); border-radius: 10px; margin-bottom: 0.75rem; background: var(--gray-50); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <strong style="font-size: 1rem;">${a.doctor_name}</strong>
            <span class="badge badge-normal" style="font-size: 0.7rem;">${a.status}</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--gray-600); margin-top: 2px;">
            ${a.doctor_specialty} • ${a.hospital}
          </div>
          <div style="font-size: 0.82rem; color: var(--gray-500); margin-top: 4px;">
            📅 <strong>${a.date}</strong> at <strong>${a.time}</strong> • Patient: ${a.patient_name}
          </div>
          ${a.report_token ? `<div style="font-size: 0.78rem; color: var(--primary); font-weight: 600; margin-top: 2px;">📎 Linked Report Token: ${a.report_token}</div>` : ""}
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Error loading appointments:", e);
  }
}

// Doctor Portal: Lookup & Scanner
async function lookupPatientReport() {
  const token = document.getElementById("doctor-token-input").value.trim();
  if (!token) {
    alert("Please enter a valid patient report access token or ID");
    return;
  }

  try {
    const res = await fetch(`/api/reports/${encodeURIComponent(token)}`);
    if (!res.ok) {
      alert("Report not found with token: " + token);
      return;
    }

    const record = await res.json();
    currentDoctorReport = record;
    renderDoctorChart(record);
  } catch (e) {
    alert("Error fetching report: " + e.message);
  }
}

function renderDoctorChart(record) {
  document.getElementById("doc-patient-empty").style.display = "none";
  document.getElementById("doc-patient-record").style.display = "block";

  document.getElementById("doc-chart-token").innerText = `TOKEN: ${record.token}`;
  document.getElementById("doc-chart-patient").innerText = record.patient_name || "Patient Record";
  document.getElementById("doc-chart-date").innerText = `Uploaded: ${new Date(record.created_at).toLocaleString()} • File: ${record.filename}`;

  const tbody = document.getElementById("doc-param-table-body");
  tbody.innerHTML = "";

  const params = record.analysis?.parameters || [];
  params.forEach(p => {
    const tr = document.createElement("tr");
    let badgeClass = "badge-normal";
    const statusLower = (p.status || "").toLowerCase();
    if (statusLower.includes("high") || statusLower.includes("elevated")) badgeClass = "badge-high";
    else if (statusLower.includes("low") || statusLower.includes("decreased")) badgeClass = "badge-low";
    else if (statusLower.includes("borderline")) badgeClass = "badge-borderline";

    tr.innerHTML = `
      <td><strong>${p.name}</strong></td>
      <td>${p.value}</td>
      <td style="color: var(--gray-600);">${p.reference_range}</td>
      <td><span class="badge ${badgeClass}">${p.status}</span></td>
    `;
    tbody.appendChild(tr);
  });

  renderDoctorNotesHistory(record.doctor_notes || []);
}

function renderDoctorNotesHistory(notes) {
  const container = document.getElementById("doc-notes-history-container");
  if (!notes || notes.length === 0) {
    container.innerHTML = `<p style="font-size: 0.85rem; color: var(--gray-500);">No prior doctor notes recorded yet.</p>`;
    return;
  }

  container.innerHTML = notes.map(n => `
    <div style="background: var(--gray-50); border: 1px solid var(--gray-200); border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
      <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 0.35rem;">
        <strong>🩺 ${n.doctor_name}</strong>
        <span style="color: var(--gray-500);">${new Date(n.created_at).toLocaleString()}</span>
      </div>
      <p style="font-size: 0.88rem; color: var(--gray-800);">${n.notes}</p>
    </div>
  `).join("");
}

async function saveDoctorClinicalNotes() {
  if (!currentDoctorReport) {
    alert("Please scan or load a patient report first.");
    return;
  }

  const doctor_name = document.getElementById("doc-signing-name").value;
  const notes = document.getElementById("doc-clinical-notes-input").value.trim();

  if (!notes) {
    alert("Please enter clinical notes before saving.");
    return;
  }

  try {
    const res = await fetch(`/api/reports/${currentDoctorReport.id}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doctor_name, notes })
    });

    const data = await res.json();
    alert("Consultation note signed and saved to patient record!");
    document.getElementById("doc-clinical-notes-input").value = "";
    currentDoctorReport = data.report;
    renderDoctorNotesHistory(data.report.doctor_notes || []);
  } catch (e) {
    alert("Failed to save doctor notes: " + e.message);
  }
}

// Camera Scanner
function toggleCameraScanner() {
  const btn = document.getElementById("btn-toggle-cam");
  if (isScannerActive) {
    if (html5QrScanner) {
      html5QrScanner.stop().then(() => {
        isScannerActive = false;
        btn.innerText = "📷 Start Camera Scanner";
      }).catch(err => console.error(err));
    }
  } else {
    html5QrScanner = new Html5Qrcode("reader");
    html5QrScanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        // Handle scanned QR
        try {
          const url = new URL(decodedText);
          const token = url.searchParams.get("token") || decodedText;
          document.getElementById("doctor-token-input").value = token;
        } catch {
          document.getElementById("doctor-token-input").value = decodedText;
        }
        lookupPatientReport();
        html5QrScanner.stop();
        isScannerActive = false;
        btn.innerText = "📷 Start Camera Scanner";
      },
      (error) => {}
    ).then(() => {
      isScannerActive = true;
      btn.innerText = "🛑 Stop Camera Scanner";
    }).catch(err => {
      alert("Camera access failed or unavailable: " + err);
    });
  }
}

async function loadRecentReportsList() {
  try {
    const res = await fetch("/api/reports");
    const reports = await res.json();
    const container = document.getElementById("doctor-recent-reports-list");
    if (!container) return;

    if (reports.length === 0) {
      container.innerHTML = `<p style="font-size: 0.8rem; color: var(--gray-500);">No patient reports uploaded yet.</p>`;
      return;
    }

    container.innerHTML = reports.map(r => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: var(--gray-50); border-radius: 6px; margin-bottom: 0.35rem; font-size: 0.82rem;">
        <div>
          <strong>${r.patient_name}</strong> • <span style="font-family: monospace; color: var(--primary);">${r.token}</span>
        </div>
        <button class="btn btn-outline btn-sm" style="padding: 2px 8px; font-size: 0.75rem;" onclick="loadSpecificToken('${r.token}')">View</button>
      </div>
    `).join("");
  } catch (e) {
    console.error("Error loading recent reports:", e);
  }
}

function loadSpecificToken(token) {
  document.getElementById("doctor-token-input").value = token;
  lookupPatientReport();
}

async function loadDoctorAppointments() {
  try {
    const res = await fetch("/api/appointments");
    const appts = await res.json();

    const container = document.getElementById("doctor-appts-list");
    if (!container) return;

    if (appts.length === 0) {
      container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--gray-500);"><p>No consultations scheduled in queue.</p></div>`;
      return;
    }

    container.innerHTML = appts.map(a => `
      <div style="padding: 1rem; border: 1px solid var(--gray-200); border-radius: 10px; margin-bottom: 0.75rem; background: var(--white); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <strong style="font-size: 1.05rem;">${a.patient_name}</strong>
            <span class="badge ${a.status === 'Completed' ? 'badge-normal' : 'badge-high'}">${a.status}</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--gray-600); margin-top: 3px;">
            Phone: ${a.patient_phone} • Attending: ${a.doctor_name}
          </div>
          <div style="font-size: 0.82rem; color: var(--gray-500); margin-top: 2px;">
            Slot: 📅 <strong>${a.date}</strong> at <strong>${a.time}</strong> • Reason: <em>"${a.reason}"</em>
          </div>
          ${a.report_token ? `
            <div style="margin-top: 4px;">
              <button class="btn btn-outline btn-sm" style="padding: 2px 8px; font-size: 0.75rem;" onclick="loadSpecificToken('${a.report_token}')">
                📄 Open Attached Report (${a.report_token})
              </button>
            </div>
          ` : ""}
        </div>
        <div style="display: flex; gap: 0.4rem;">
          <button class="btn btn-outline btn-sm" onclick="updateApptStatus('${a.id}', 'In Consultation')">Consulting</button>
          <button class="btn btn-primary btn-sm" onclick="updateApptStatus('${a.id}', 'Completed')">Complete</button>
        </div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Error loading doctor appointments:", e);
  }
}

async function updateApptStatus(apptId, status) {
  try {
    await fetch(`/api/appointments/${apptId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    loadDoctorAppointments();
  } catch (e) {
    alert("Failed to update status: " + e.message);
  }
}

// ==========================================
// RAG CLINICAL & APPOINTMENT CHATBOT (Web Speech + AI Chat + Grounded RAG)
// ==========================================

let chatHistory = [];
let isChatSubmitting = false;

function initVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Speech recognition not natively supported in this browser.");
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = false;
  speechRecognition.lang = "en-US";

  speechRecognition.onstart = () => {
    isRecordingVoice = true;
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) micBtn.classList.add("listening");
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    const input = document.getElementById("chat-text-input");
    if (input) input.value = transcript;
    submitChatMessage();
  };

  speechRecognition.onerror = (event) => {
    console.error("Speech Recognition Error:", event.error);
    isRecordingVoice = false;
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) micBtn.classList.remove("listening");
  };

  speechRecognition.onend = () => {
    isRecordingVoice = false;
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) micBtn.classList.remove("listening");
  };
}

function toggleVoiceRecording() {
  if (!speechRecognition) {
    initVoiceRecognition();
    if (!speechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use keyboard text input.");
      return;
    }
  }

  if (isRecordingVoice) {
    speechRecognition.stop();
  } else {
    try {
      speechRecognition.start();
    } catch (e) {
      console.warn("Speech recognition already active or restarting", e);
    }
  }
}

function sendChatPrompt(prompt) {
  const input = document.getElementById("chat-text-input");
  if (input) {
    input.value = prompt;
    submitChatMessage();
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

function formatChatMarkdown(text) {
  if (!text) return "";
  let formatted = escapeHtml(text);
  
  // Format bold **text**
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Format italics *text*
  formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Format blockquotes (> note)
  formatted = formatted.replace(/^(&gt;|>)\s?(.*)$/gm, '<blockquote>$2</blockquote>');
  
  // Format bullet points (• or -)
  const lines = formatted.split('\n');
  let inList = false;
  let resultLines = [];
  
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      if (!inList) {
        resultLines.push('<ul style="margin: 0.35rem 0 0.5rem 1rem; padding-left: 0.5rem;">');
        inList = true;
      }
      resultLines.push(`<li>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        resultLines.push('</ul>');
        inList = false;
      }
      if (trimmed.length > 0) {
        resultLines.push(`<p style="margin-bottom: 0.4rem;">${line}</p>`);
      }
    }
  }
  if (inList) {
    resultLines.push('</ul>');
  }
  
  return resultLines.join('\n');
}

async function submitChatMessage() {
  if (isChatSubmitting) return;
  const input = document.getElementById("chat-text-input");
  const message = input ? input.value.trim() : "";
  if (!message) return;

  // Clear input
  input.value = "";
  
  const msgBox = document.getElementById("chat-messages-box");
  if (!msgBox) return;

  // Append user message
  const userRow = document.createElement("div");
  userRow.className = "chat-msg-row user";
  userRow.innerHTML = `
    <div class="chat-bubble">
      <p>${escapeHtml(message)}</p>
    </div>
    <div class="chat-avatar">👤</div>
  `;
  msgBox.appendChild(userRow);

  // Append loading indicator
  const loadingRow = document.createElement("div");
  loadingRow.className = "chat-msg-row assistant";
  loadingRow.id = "chat-msg-loading";
  loadingRow.innerHTML = `
    <div class="chat-avatar">🩺</div>
    <div class="chat-bubble">
      <p style="color: var(--gray-500); font-style: italic;">
        <span>🔍</span> Searching laboratory values & clinical knowledge base...
      </p>
    </div>
  `;
  msgBox.appendChild(loadingRow);
  msgBox.scrollTop = msgBox.scrollHeight;

  isChatSubmitting = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        report_id: currentReport ? currentReport.id : null,
        history: chatHistory.slice(-8) // Send recent context
      })
    });

    const data = await res.json();
    
    // Remove loading row
    const loadingEl = document.getElementById("chat-msg-loading");
    if (loadingEl) loadingEl.remove();

    if (data.reply) {
      chatHistory.push({ role: "user", content: message });
      chatHistory.push({ role: "assistant", content: data.reply });

      // Render assistant message
      renderAssistantChatMessage(data.reply, data.doctor_recommendation, data.parameters_cited);

      // Text-To-Speech if enabled
      const ttsCheckbox = document.getElementById("chat-tts-toggle");
      if (ttsCheckbox && ttsCheckbox.checked) {
        // Strip markdown and emojis for speech
        const speechCleanText = data.reply
          .replace(/\*\*/g, "")
          .replace(/[•#>\-]/g, "")
          .replace(/[\u{1F600}-\u{1F6FF}]/gu, "");
        speakText(speechCleanText);
      }
    } else {
      renderAssistantChatMessage("Sorry, I could not process your query at this moment. Please try again.");
    }
  } catch (e) {
    const loadingEl = document.getElementById("chat-msg-loading");
    if (loadingEl) loadingEl.remove();
    renderAssistantChatMessage(`Error communicating with RAG assistant: ${e.message}`);
  } finally {
    isChatSubmitting = false;
    msgBox.scrollTop = msgBox.scrollHeight;
  }
}

function renderAssistantChatMessage(replyText, doctorRec, paramsCited) {
  const msgBox = document.getElementById("chat-messages-box");
  if (!msgBox) return;

  const assistantRow = document.createElement("div");
  assistantRow.className = "chat-msg-row assistant";

  let doctorHtml = "";
  if (doctorRec) {
    const availableSlots = doctorRec.available_slots ? doctorRec.available_slots.slice(0, 3).join(", ") : "Flexible slots available";
    doctorHtml = `
      <div class="doc-booking-card-inline">
        <div class="doc-meta">
          <div class="doc-avatar">${doctorRec.avatar || "👨‍⚕️"}</div>
          <div>
            <div class="doc-name">${doctorRec.name}</div>
            <div class="doc-spec">${doctorRec.specialty} • ${doctorRec.hospital}</div>
            <div class="doc-slots">🕒 Available: ${availableSlots}</div>
          </div>
        </div>
        <div style="margin-top: 0.65rem; text-align: right;">
          <button class="btn btn-primary btn-sm" onclick="bookDoctorInline('${doctorRec.id}', '${doctorRec.name}', '${doctorRec.specialty}')">
            📅 Book Appointment with ${doctorRec.name} →
          </button>
        </div>
      </div>
    `;
  }

  assistantRow.innerHTML = `
    <div class="chat-avatar">🩺</div>
    <div class="chat-bubble">
      ${formatChatMarkdown(replyText)}
      ${doctorHtml}
    </div>
  `;

  msgBox.appendChild(assistantRow);
  msgBox.scrollTop = msgBox.scrollHeight;
}

function bookDoctorInline(doctorId, doctorName, specialty) {
  // Switch to booking tab
  switchPatientTab("book");

  // Select doctor in the grid
  const docCards = document.querySelectorAll(".doctor-card-select");
  doctorsList.forEach((d, idx) => {
    if (d.id === doctorId && docCards[idx]) {
      selectDoctor(d.id, docCards[idx]);
    }
  });

  // Pre-fill fields if report is available
  if (currentReport) {
    const tokenInput = document.getElementById("appt-report-token");
    const nameInput = document.getElementById("appt-patient-name");
    const reasonInput = document.getElementById("appt-reason");
    if (tokenInput) tokenInput.value = currentReport.token;
    if (nameInput) nameInput.value = currentReport.patient_name || "";
    if (reasonInput) reasonInput.value = `Consultation for laboratory review (${specialty})`;
  }

  // Scroll to booking form smoothly
  const bookTab = document.getElementById("patient-tab-book");
  if (bookTab) {
    bookTab.scrollIntoView({ behavior: "smooth" });
  }
}

function speakText(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // Stop any previous speech
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.lang = "en-US";
  window.speechSynthesis.speak(utterance);
}

// ==========================================
// MEDICAL KNOWLEDGE BASE & LAB GUIDE LOADER
// ==========================================
async function loadMedicalKnowledgeBase() {
  try {
    const res = await fetch("/api/knowledge-base");
    const kb = await res.json();

    // 1. Render Panels Grid
    const panelsGrid = document.getElementById("kb-panels-grid");
    if (panelsGrid && kb.panels) {
      panelsGrid.innerHTML = Object.entries(kb.panels).map(([key, p]) => `
        <div class="card">
          <div class="card-header">
            <h3 class="card-title" style="font-size: 1.05rem;">
              <span>${key === 'cbc' ? '🩸' : (key === 'thyroid' ? '🦋' : (key === 'liver' ? '🫀' : (key === 'kidney' ? '🧪' : '📊')))}</span>
              ${p.name}
            </h3>
            <span class="badge badge-normal" style="font-size: 0.7rem;">Clinical Panel</span>
          </div>
          <p style="font-size: 0.88rem; color: var(--gray-700); margin-bottom: 0.75rem; line-height: 1.5;">
            ${p.clinical_overview}
          </p>
          <div style="background: var(--gray-50); padding: 0.65rem 0.85rem; border-radius: 8px; font-size: 0.8rem; margin-bottom: 0.65rem;">
            <strong>Clinical Purpose:</strong> ${p.clinical_purpose}
          </div>
          <div style="font-size: 0.78rem; color: var(--gray-600); margin-bottom: 0.5rem;">
            <strong>Key Indicators:</strong> ${p.primary_indicators ? p.primary_indicators.join(" • ") : ""}
          </div>
          <div style="font-size: 0.75rem; color: var(--primary-dark); font-weight: 600;">
            📖 Reference Source: ${p.reference_source}
          </div>
        </div>
      `).join("");
    }

    // 2. Render Core Interpretation Principles Grid
    const principlesGrid = document.getElementById("kb-principles-grid");
    if (principlesGrid && kb.reference_range_limitations_guide?.core_principles) {
      principlesGrid.innerHTML = kb.reference_range_limitations_guide.core_principles.map((cp, idx) => `
        <div style="background: var(--gray-50); border: 1px solid var(--gray-200); border-radius: 10px; padding: 1rem;">
          <h4 style="font-size: 0.92rem; font-weight: 700; color: #0f766e; margin-bottom: 0.35rem;">
            ${idx + 1}. ${cp.principle}
          </h4>
          <p style="font-size: 0.84rem; color: var(--gray-700); line-height: 1.5;">
            ${cp.explanation}
          </p>
        </div>
      `).join("");
    }

    // 3. Render Authoritative References
    const refList = document.getElementById("kb-references-list");
    if (refList && kb.reference_range_limitations_guide?.authoritative_references) {
      refList.innerHTML = kb.reference_range_limitations_guide.authoritative_references.map(r => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; background: var(--gray-50); border: 1px solid var(--gray-200); border-radius: 8px; flex-wrap: wrap; gap: 0.5rem;">
          <div>
            <strong style="font-size: 0.92rem; color: var(--gray-800); display: block;">${r.organization}</strong>
            <span style="font-size: 0.82rem; color: var(--gray-600);">${r.resource}</span>
          </div>
          <a href="${r.url}" target="_blank" class="btn btn-outline btn-sm" style="font-size: 0.78rem; text-decoration: none;">
            Explore Guidelines ↗
          </a>
        </div>
      `).join("");
    }

  } catch (e) {
    console.error("Failed to load medical knowledge base:", e);
  }
}

