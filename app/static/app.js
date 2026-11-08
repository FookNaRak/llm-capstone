const output = document.querySelector("#output");
const statuses = {
  compatible: "ผ่านตามกฎที่ตรวจ",
  incompatible: "พบสเปกที่ใช้ร่วมกันไม่ได้",
  conditional: "ใช้ได้เมื่อผ่านเงื่อนไข BIOS",
  unknown: "ข้อมูลไม่พอสำหรับสรุป",
};

function append(parent, tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
}

function render(data) {
  output.replaceChildren();
  const check = data.result || (data.checks ? data : null);
  if (check) {
    append(output, "h2", "ผลตรวจจากแคตตาล็อก");
    append(output, "p", statuses[check.status], "status " + check.status);
    const parts = Object.values(check.parts).join(" · ");
    if (parts) append(output, "p", parts);
    const list = append(output, "ul", "");
    for (const item of check.checks) {
      const candidates = item.candidates?.length ? " " + item.candidates.join(" / ") : "";
      append(list, "li", item.detail + candidates);
    }
  }
  if (data.answer) {
    append(output, "h3", check ? "คำอธิบายจากผู้ช่วย" : "ข้อความจากผู้ช่วย · ยังไม่มีผลตรวจ");
    append(output, "p", data.answer, "answer");
  }
  if (data.citations?.length) {
    append(output, "h3", "แหล่งข้อมูลผู้ผลิต");
    const list = append(output, "ul", "");
    for (const citation of data.citations) {
      const link = append(append(list, "li", ""), "a", citation.title);
      link.href = citation.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  }
  if (data.trace?.length) {
    const details = append(output, "details", "");
    append(details, "summary", "เครื่องมือที่เรียก");
    const list = append(details, "ol", "");
    for (const call of data.trace) append(list, "li", call.name + (call.ok ? " ✓" : " ✗"));
  }
}

async function submit(event, endpoint) {
  event.preventDefault();
  const data = Object.fromEntries([...new FormData(event.currentTarget)].filter(([, value]) => value));
  output.hidden = false;
  output.textContent = "กำลังตรวจข้อมูล…";
  const buttons = [...document.querySelectorAll("button")];
  for (const button of buttons) button.disabled = true;
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error);
    render(body);
  } catch (error) {
    output.textContent = error.message;
  } finally {
    for (const button of buttons) button.disabled = false;
  }
}

document.querySelector("#ask").addEventListener("submit", event => submit(event, "/api/ask"));
document.querySelector("#check").addEventListener("submit", event => submit(event, "/api/check"));

fetch("/api/parts")
  .then(response => {
    if (!response.ok) throw new Error("โหลดแคตตาล็อกไม่สำเร็จ");
    return response.json();
  })
  .then(({ parts }) => {
    for (const part of parts) {
      const select = document.getElementById(part.kind);
      select.add(new Option(part.name, part.id));
    }
  })
  .catch(error => {
    output.hidden = false;
    output.textContent = error.message;
  });
