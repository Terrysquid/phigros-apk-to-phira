let canvas;
let ctx;
let startTime;
let chart, music;
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
  audio = new Audio("music.wav");
  bgImage = new Image();
  bgImage.src = "illustration.jpg";
  await loadChart();
  canvas.addEventListener(
    "click",
    async () => {
      audio.currentTime = 0;
      await audio.play();
      requestAnimationFrame(loop);
    },
    { once: true }
  );
}

function resizeCanvas() {
  canvas.width = canvas.getBoundingClientRect().width;
  canvas.height = canvas.getBoundingClientRect().height;
  lineLength = 3 * canvas.width;
}

async function loadChart() {
  const res = await fetch("chart.json");
  chart = await res.json();
}

function drawLine(real_time) {
  if (!chart) return;
  ctx.strokeStyle = "#FFFFBB";
  ctx.lineWidth = (1 / 160) * canvas.height;
  for (let l = 0; l < chart.judgeLineList.length; l++) {
    let line = chart.judgeLineList[l];
    let cx = 0;
    let cy = 0;
    let angle = 0;
    let alpha = 1;
    let time = ((real_time * line.bpm) / 60) * 32;
    let events = line.judgeLineMoveEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        let x = (e.end - e.start) * p + e.start;
        let y = (e.end2 - e.start2) * p + e.start2;
        cx = x * canvas.width;
        cy = (1 - y) * canvas.height;
        break;
      }
    }
    events = line.judgeLineRotateEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        let ang = (e.end - e.start) * p + e.start;
        angle = -(ang * Math.PI) / 180;
        break;
      }
    }
    events = line.judgeLineDisappearEvents;
    for (let i = 0; i < events.length; i++) {
      let e = events[i];
      if (time >= e.startTime && time <= e.endTime) {
        let p = (time - e.startTime) / (e.endTime - e.startTime);
        alpha = (e.end - e.start) * p + e.start;
        break;
      }
    }
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.beginPath();
    ctx.moveTo(-lineLength, 0);
    ctx.lineTo(lineLength, 0);
    ctx.stroke();
    ctx.globalAlpha = 1;
    let notes = line.notesAbove;
    for (let i = 0; i < notes.length; i++) {
      let note = notes[i];
      ctx.strokeStyle = ["#51fcff", "#FFFFBB", "#5d5bff", "#ff8787"][
        note.type - 1
      ];
      let dt = time - note.time;
      ctx.beginPath();
      ctx.moveTo(-50 + note.positionX * 80, dt * 8);
      ctx.lineTo(50 + note.positionX * 80, dt * 8);
      if (note.type == 3) {
        ctx.moveTo(note.positionX * 80, dt * 8);
        ctx.lineTo(note.positionX * 80, (dt - note.holdTime) * 8);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
}

function loop() {
  let real_time = audio.currentTime;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawLine(real_time);
  if (!audio.ended) {
    requestAnimationFrame(loop);
  }
}
