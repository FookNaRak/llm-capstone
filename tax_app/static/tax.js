const baht = new Intl.NumberFormat("th-TH", {style: "currency", currency: "THB"});

function add(parent, tag, text) {
  const element = document.createElement(tag);
  element.textContent = text;
  parent.append(element);
  return element;
}

function render(output, data) {
  output.replaceChildren();
  const result = data.result;
  if (result) {
    add(output, "h2", "ประมาณการภาษีปี 2568");
    const summary = add(output, "div", "");
    summary.className = "summary";
    for (const [label, value] of [
      ["ภาษีหลังลดหย่อน", result.tax],
      ["ภาษีที่ประหยัดได้", result.tax_saved],
      ["เงินได้สุทธิ", result.net_income],
    ]) {
      const card = add(summary, "div", "");
      add(card, "span", label);
      add(card, "strong", baht.format(Number(value)));
    }
    const table = add(output, "table", "");
    const rows = [
      ["รายได้ที่ใช้คำนวณ", result.inputs.annual_income],
      ["ค่าใช้จ่ายเงินเดือน", result.expense],
      ["ค่าลดหย่อนส่วนตัว", result.personal],
      ["ประกันชีวิตที่ใช้สิทธิได้", result.allowed.life_premium],
      ["ประกันสุขภาพที่ใช้สิทธิได้", result.allowed.health_premium],
      ["Easy E-Receipt วงเงินทั่วไป", result.allowed.receipt_base],
      ["Easy E-Receipt วงเงินเพิ่ม", result.allowed.receipt_extra],
      ["ภาษีก่อนหักประกันและ Easy E-Receipt", result.tax_before_optional],
    ];
    for (const [label, value] of [
      ["เบี้ยประกันชีวิตส่วนที่เกินเพดาน", result.disallowed.life_premium],
      ["เบี้ยประกันสุขภาพส่วนที่เกินเพดาน", result.disallowed.health_premium],
      ["ยอด Easy E-Receipt ส่วนที่เกินเพดาน", result.disallowed.receipts],
    ]) {
      if (Number(value) > 0) rows.push([label, value]);
    }
    if (result.balance !== null) {
      const balance = Number(result.balance);
      rows.push([balance < 0 ? "ภาษีที่ชำระไว้เกิน" : "ภาษีที่ต้องชำระเพิ่ม", Math.abs(balance)]);
    }
    for (const [label, value] of rows) {
      const row = table.insertRow();
      add(row, "th", label).scope = "row";
      add(row, "td", baht.format(Number(value)));
    }
  }
  if (data.answer) add(output, "p", data.answer).className = "answer";
  if (data.citations?.length) {
    add(output, "h3", "เอกสารกรมสรรพากร");
    const list = add(output, "ul", "");
    for (const rule of data.citations) {
      const link = add(add(list, "li", ""), "a", rule.title + " (หน้า " + rule.page + ")");
      link.href = rule.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  }
  if (data.trace?.length) {
    const details = add(output, "details", "");
    add(details, "summary", "เครื่องมือที่ผู้ช่วยเรียก");
    const list = add(details, "ol", "");
    for (const call of data.trace) add(list, "li", call.name + (call.ok ? " ✓" : " ✗"));
  }
}

async function request(endpoint, body) {
  const response = await fetch("/api/" + endpoint, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}

document.getElementById("calculate").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const body = {tax_year: 2568};
  for (const [key, value] of new FormData(form)) {
    if (value !== "") body[key] = Number(value);
  }
  const button = form.querySelector("button");
  const output = document.getElementById("output");
  button.disabled = true;
  output.textContent = "กำลังคำนวณ…";
  try {
    render(output, await request("calculate", body));
  } catch (error) {
    output.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

const chatForm = document.getElementById("ask");
const composer = chatForm.elements.query;
const send = chatForm.querySelector("button");
const chatLog = document.getElementById("chat-output");
const intro = document.getElementById("chat-intro");
const newChat = document.getElementById("new-chat");
const history = [];

function chatMessage(role, label) {
  const message = add(chatLog, "div", "");
  message.className = "chat-message chat-" + role;
  add(message, "strong", label).className = "chat-label";
  return add(message, "div", "");
}

function scrollChat() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

newChat.addEventListener("click", () => {
  history.length = 0;
  chatLog.replaceChildren();
  chatLog.hidden = true;
  intro.hidden = false;
  newChat.hidden = true;
  composer.value = "";
  composer.focus();
});

composer.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault();
    if (!send.disabled && composer.value.trim()) chatForm.requestSubmit();
  }
});

chatForm.addEventListener("submit", async event => {
  event.preventDefault();
  const query = composer.value.trim();
  if (!query || send.disabled) return;

  intro.hidden = true;
  newChat.hidden = false;
  chatLog.hidden = false;
  add(chatMessage("user", "คุณ"), "p", query).className = "answer";
  const reply = chatMessage("assistant", "ผู้ช่วยภาษี");
  reply.textContent = "กำลังตอบ…";
  scrollChat();
  composer.value = "";
  composer.readOnly = true;
  send.disabled = true;
  newChat.disabled = true;
  try {
    const data = await request("ask", {query, history});
    render(reply, data);
    const answer = Array.from((data.answer || "").trim()).slice(0, 1200).join("").trim();
    if (answer) {
      history.push({role: "user", content: query}, {role: "assistant", content: answer});
      while (history.length > 8 ||
             history.reduce((total, message) => total + message.content.length, 0) > 4000) {
        history.splice(0, 2);
      }
    }
  } catch (error) {
    reply.textContent = error.message;
    reply.classList.add("chat-error");
    composer.value = query;
  } finally {
    composer.readOnly = false;
    send.disabled = false;
    newChat.disabled = false;
    scrollChat();
  }
});
