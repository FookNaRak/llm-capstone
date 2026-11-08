const output = document.querySelector("#output");
const baht = new Intl.NumberFormat("th-TH", {style: "currency", currency: "THB"});

function add(parent, tag, text) {
  const element = document.createElement(tag);
  element.textContent = text;
  parent.append(element);
  return element;
}

function render(data) {
  output.replaceChildren();
  const result = data.result;
  if (result) {
    add(output, "h2", "ประมาณการภาษีปี 2568");
    const table = add(output, "table", "");
    const rows = [
      ["รายได้ที่ใช้คำนวณ", result.inputs.annual_income],
      ["ค่าใช้จ่ายเงินเดือน", result.expense],
      ["ค่าลดหย่อนส่วนตัว", result.personal],
      ["ประกันชีวิตที่ใช้สิทธิได้", result.allowed.life_premium],
      ["ประกันสุขภาพที่ใช้สิทธิได้", result.allowed.health_premium],
      ["Easy E-Receipt วงเงินทั่วไป", result.allowed.receipt_base],
      ["Easy E-Receipt วงเงินเพิ่ม", result.allowed.receipt_extra],
      ["เงินได้สุทธิ", result.net_income],
      ["ภาษีก่อนหักประกันและ Easy E-Receipt", result.tax_before_optional],
      ["ภาษีหลังหักรายการที่กรอก", result.tax],
      ["ภาษีลดลง", result.tax_saved],
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

for (const id of ["calculate", "ask"]) {
  document.getElementById(id).addEventListener("submit", async event => {
    event.preventDefault();
    const entries = [...new FormData(event.currentTarget)];
    const body = id === "ask" ? Object.fromEntries(entries) : {tax_year: 2568};
    if (id === "calculate") {
      for (const [key, value] of entries) {
        if (value !== "") body[key] = Number(value);
      }
    }
    const buttons = [...document.querySelectorAll("button")];
    buttons.forEach(button => { button.disabled = true; });
    output.hidden = false;
    output.textContent = "กำลังตรวจข้อมูล…";
    try {
      const response = await fetch("/api/" + id, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      render(data);
    } catch (error) {
      output.textContent = error.message;
    } finally {
      buttons.forEach(button => { button.disabled = false; });
    }
  });
}
