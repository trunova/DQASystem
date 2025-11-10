const apiBase = window.location.origin; 

const $ = (id) => document.getElementById(id);

async function uploadFile() {
  const file = $("fileInput").files[0];
  if (!file) {
    $("uploadStatus").innerHTML = `<span class="pill warn">Выберите .docx</span>`;
    return;
  }
  const form = new FormData();
  form.append("file", file);

  $("uploadStatus").innerHTML = `Загружаю…`;
  try {
    const res = await fetch(`${apiBase}/files`, { method: "POST", body: form });
    if (!res.ok) {
      const txt = await res.text();
      $("uploadStatus").innerHTML = `<span class="pill err">Ошибка ${res.status}</span><pre>${txt}</pre>`;
      return;
    }
    const data = await res.json();
    $("uploadStatus").innerHTML = `<span class="pill ok">OK</span> file_id: <code>${data.file_id}</code>`;
    $("fileIdInput").value = data.file_id;
  } catch (e) {
    $("uploadStatus").innerHTML = `<span class="pill err">Ошибка</span><pre>${e}</pre>`;
  }
}

async function askQuestion() {
  const fileId = $("fileIdInput").value.trim();
  const question = $("questionInput").value.trim();
  if (!fileId || !question) {
    $("askStatus").innerHTML = `<span class="pill warn">Нужны file_id и вопрос</span>`;
    return;
  }
  $("askStatus").innerHTML = `Отправляю вопрос…`;
  try {
    const res = await fetch(`${apiBase}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: fileId, question })
    });
    if (!res.ok) {
      const txt = await res.text();
      $("askStatus").innerHTML = `<span class="pill err">Ошибка ${res.status}</span><pre>${txt}</pre>`;
      return;
    }
    const data = await res.json();
    $("askStatus").innerHTML = `<span class="pill ok">OK</span> question_id: <code>${data.question_id}</code>`;
    $("questionIdInput").value = data.question_id;

    pollAnswer(data.question_id);
  } catch (e) {
    $("askStatus").innerHTML = `<span class="pill err">Ошибка</span><pre>${e}</pre>`;
  }
}

async function pollAnswer(qid, maxTries = 30, delayMs = 1200) {
  $("answerBox").innerHTML = `Жду ответ…`;
  for (let i = 0; i < maxTries; i++) {
    const res = await fetch(`${apiBase}/answers/${qid}`);
    if (!res.ok) {
      const txt = await res.text();
      $("answerBox").innerHTML = `<span class="pill err">Ошибка ${res.status}</span><pre>${txt}</pre>`;
      return;
    }
    const data = await res.json();
    if (data.status === "PENDING") {
      await new Promise(r => setTimeout(r, delayMs));
      continue;
    }
    if (data.status === "DONE") {
      const refs = (data.references || []).map(r => `#${r.rank}. ${escapeHtml(r.snippet)}`).join("\n\n");
      $("answerBox").innerHTML =
        `<div><span class="pill ok">DONE</span></div>
         <div style="margin-top:8px;"><strong>Ответ:</strong><pre>${escapeHtml(data.answer || "")}</pre></div>
         <div style="margin-top:8px;"><strong>Фрагменты:</strong><pre>${refs}</pre></div>`;
      return;
    }
    if (data.status === "ERROR") {
      $("answerBox").innerHTML =
        `<div><span class="pill err">ERROR</span></div>
         <pre>${escapeHtml(data.answer || "Ошибка")}</pre>`;
      return;
    }
  }
  $("answerBox").innerHTML = `<span class="pill warn">Истек таймаут ожидания</span>`;
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"'`=\/]/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'}[c]);
  });
}

$("uploadBtn").addEventListener("click", uploadFile);
$("askBtn").addEventListener("click", askQuestion);
$("checkBtn").addEventListener("click", () => {
  const qid = $("questionIdInput").value.trim();
  if (qid) pollAnswer(qid);
});
