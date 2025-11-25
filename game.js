let canvas;
let ctx;
let startTime = null;
let chart = null;
let lineLength = 0;

window.addEventListener("load", init);
window.addEventListener("resize", () => {
  if (!canvas || !ctx) return;
  resizeCanvas();
});

async function init() {
  canvas = document.getElementById("canvas");
  ctx = canvas.getContext("2d");
  resizeCanvas();
  await loadChart();
  requestAnimationFrame(loop);
}

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  ctx.setTransform(1, 0, 0, -1, 0, canvas.height);
  lineLength = 3 * canvas.width;
}

async function loadChart() {
  const res = await fetch("chart.json");
  chart = await res.json();
}

function drawLine(real_time) {
  if (!chart) return;
  ctx.strokeStyle = "#FDFDBA";
  ctx.lineWidth = (1 / 160) * canvas.height;
  for (let l = 0; l < chart.judgeLineList.length; l++) {
    let cx = 0;
    let cy = 0;
    let angle = 0;
    let alpha = 1;
    let time = real_time * chart.judgeLineList[l].bpm / 60 * 32;
    let events = chart.judgeLineList[l].judgeLineMoveEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        let x = (e.end - e.start) * p + e.start;
        let y = (e.end2 - e.start2) * p + e.start2;
        cx = x * canvas.width;
        cy = y * canvas.height;
        break;
      }
    }
    events = chart.judgeLineList[l].judgeLineRotateEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        let ang = (e.end - e.start) * p + e.start;
        angle = (ang * Math.PI) / 180;
        break;
      }
    }
    events = chart.judgeLineList[l].judgeLineDisappearEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        alpha = (e.end - e.start) * p + e.start;
        break;
      }
    }
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.moveTo(
      cx - lineLength * Math.cos(angle),
      cy - lineLength * Math.sin(angle)
    );
    ctx.lineTo(
      cx + lineLength * Math.cos(angle),
      cy + lineLength * Math.sin(angle)
    );
    ctx.stroke();
  }
}

function loop(timestamp) {
  if (startTime == null) startTime = timestamp;
  let real_time = ((timestamp - startTime) / 1000);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawLine(real_time);
  requestAnimationFrame(loop);
}
