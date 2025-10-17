let linesData = {}; // { "page1.jpg": [x1, x2, ...], ... }
let currentLine = null; // línea que se está moviendo
let offsetX = 0; // diferencia entre clic y posición de la línea

function addLine(event, page) {
  const img = event.target;
  const rect = img.getBoundingClientRect();
  const x = event.clientX - rect.left;

  if (!linesData[page]) linesData[page] = [];
  linesData[page].push(x);

  // Crear la línea
  const line = document.createElement("div");
  line.className = "line absolute top-0 w-[2px] bg-red-500 cursor-ew-resize";
  line.style.left = x + "px";
  line.style.height = img.clientHeight + "px";
  line.dataset.page = page;
  line.dataset.index = linesData[page].length - 1;

  // Hacer la línea arrastrable
  line.addEventListener("mousedown", startMove);

  document.getElementById("lines-" + page).appendChild(line);
}

function startMove(e) {
  currentLine = e.target;
  const rect = currentLine.getBoundingClientRect();
  offsetX = e.clientX - rect.left;
  document.addEventListener("mousemove", moveLine);
  document.addEventListener("mouseup", stopMove);
  e.preventDefault(); // evitar selección de texto
}

function moveLine(e) {
  if (!currentLine) return;
  const page = currentLine.dataset.page;
  const container = document.getElementById("lines-" + page);
  const rect = container.getBoundingClientRect();

  // nueva posición relativa a la imagen
  let x = e.clientX - rect.left - offsetX;
  x = Math.max(0, Math.min(x, rect.width)); // limitar dentro de la imagen

  currentLine.style.left = x + "px";
  // actualizar datos
  const index = parseInt(currentLine.dataset.index);
  linesData[page][index] = x;
}

function stopMove() {
  currentLine = null;
  document.removeEventListener("mousemove", moveLine);
  document.removeEventListener("mouseup", stopMove);
}

function saveLines(pdfname) {
  fetch("/save_lines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdfname: pdfname, lines: linesData }),
  })
    .then((res) => res.json())
    .then((data) => alert("Líneas guardadas en: " + data.saved_to))
    .catch((err) => console.error(err));
}

// Función para replicar líneas de una página a todas las demás
function replicateLines(page) {
  console.log(page);

  if (!linesData[page] || linesData[page].length === 0) return;

  // recorrer todas las páginas
  for (let otherPage in linesData) {
    if (otherPage === page) continue; // saltar la original

    // eliminar líneas existentes en el DOM
    const container = document.getElementById("lines-" + otherPage);
    container.innerHTML = "";
    linesData[otherPage] = [];

    const img = container.previousElementSibling; // la imagen
    const height = img.clientHeight;

    // replicar cada línea
    linesData[page].forEach((x, index) => {
      linesData[otherPage].push(x);

      const line = document.createElement("div");
      line.className =
        "line absolute top-0 w-[2px] bg-red-500 cursor-ew-resize";
      line.style.left = x + "px";
      line.style.height = height + "px";
      line.dataset.page = otherPage;
      line.dataset.index = index;

      // permitir mover las líneas
      line.addEventListener("mousedown", startMove);

      container.appendChild(line);
    });
  }
}
