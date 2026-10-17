"use strict";

const clock = document.querySelector("#clock");
const date = document.querySelector("#date");
const timeFormat = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const dateFormat = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });

function updateClock() {
  const now = new Date();
  clock.textContent = timeFormat.format(now);
  clock.dateTime = now.toISOString();
  clock.setAttribute("aria-label", `Horário local: ${clock.textContent}`);
  date.textContent = dateFormat.format(now);
}

updateClock();
setInterval(updateClock, 1000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) updateClock();
});

document.querySelector("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#search");
  const text = input.value.trim();
  if (!text) {
    input.focus();
    return;
  }
  const status = document.querySelector("#search-status");
  status.textContent = "";
  try {
    await chrome.search.query({ text, disposition: "CURRENT_TAB" });
  } catch {
    status.textContent = "Não foi possível pesquisar. Use a barra de endereço do navegador.";
  }
});
