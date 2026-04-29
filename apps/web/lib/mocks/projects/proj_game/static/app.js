// Permit Pong. Two paddles, one ball, a permit log on the right. Each
// paddle hit appends a fake permit signature to the log. First to 10 wins.

const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const log = document.getElementById("permits");

const W = canvas.width;
const H = canvas.height;
const PADDLE_W = 10;
const PADDLE_H = 60;
const BALL = 7;

const state = {
  left: { y: H / 2 - PADDLE_H / 2, score: 0 },
  right: { y: H / 2 - PADDLE_H / 2, score: 0 },
  ball: { x: W / 2, y: H / 2, vx: 220, vy: 140 },
  paused: false,
  winner: null
};

const keys = new Set();
window.addEventListener("keydown", (e) => {
  keys.add(e.key);
  if (state.winner && (e.key === " " || e.key === "Enter")) reset();
});
window.addEventListener("keyup", (e) => keys.delete(e.key));

function rng() {
  return Math.random();
}

function fakePermit(side) {
  // Sixteen-byte deterministic-ish signature so the demo feels grounded.
  const hex = "0123456789abcdef";
  let sig = "";
  for (let i = 0; i < 16; i++) sig += hex[Math.floor(rng() * 16)];
  return { side, sig, t: new Date().toLocaleTimeString() };
}

function pushPermit(p) {
  const li = document.createElement("li");
  li.innerHTML = `<b>${p.side}</b> ${p.t} sig 0x${p.sig}`;
  log.prepend(li);
  while (log.children.length > 40) log.removeChild(log.lastChild);
}

function reset() {
  state.left.score = 0;
  state.right.score = 0;
  state.ball = { x: W / 2, y: H / 2, vx: 220 * (rng() > 0.5 ? 1 : -1), vy: 140 * (rng() > 0.5 ? 1 : -1) };
  state.winner = null;
  log.innerHTML = "";
}

function tick(dt) {
  if (state.winner) return;
  // Paddle input.
  const speed = 360;
  if (keys.has("w") || keys.has("W")) state.left.y -= speed * dt;
  if (keys.has("s") || keys.has("S")) state.left.y += speed * dt;
  if (keys.has("ArrowUp")) state.right.y -= speed * dt;
  if (keys.has("ArrowDown")) state.right.y += speed * dt;
  state.left.y = Math.max(0, Math.min(H - PADDLE_H, state.left.y));
  state.right.y = Math.max(0, Math.min(H - PADDLE_H, state.right.y));

  // Ball motion.
  state.ball.x += state.ball.vx * dt;
  state.ball.y += state.ball.vy * dt;

  // Top/bottom bounce.
  if (state.ball.y < BALL) {
    state.ball.y = BALL;
    state.ball.vy = -state.ball.vy;
  }
  if (state.ball.y > H - BALL) {
    state.ball.y = H - BALL;
    state.ball.vy = -state.ball.vy;
  }

  // Paddle collisions.
  if (
    state.ball.x < 16 + PADDLE_W &&
    state.ball.y > state.left.y &&
    state.ball.y < state.left.y + PADDLE_H &&
    state.ball.vx < 0
  ) {
    state.ball.vx = -state.ball.vx * 1.04;
    pushPermit(fakePermit("left"));
  }
  if (
    state.ball.x > W - 16 - PADDLE_W &&
    state.ball.y > state.right.y &&
    state.ball.y < state.right.y + PADDLE_H &&
    state.ball.vx > 0
  ) {
    state.ball.vx = -state.ball.vx * 1.04;
    pushPermit(fakePermit("right"));
  }

  // Score.
  if (state.ball.x < 0) {
    state.right.score++;
    serve(-1);
  }
  if (state.ball.x > W) {
    state.left.score++;
    serve(1);
  }

  if (state.left.score >= 10) state.winner = "Left wins";
  if (state.right.score >= 10) state.winner = "Right wins";
}

function serve(direction) {
  state.ball.x = W / 2;
  state.ball.y = H / 2;
  state.ball.vx = 220 * direction;
  state.ball.vy = 140 * (rng() > 0.5 ? 1 : -1);
}

function draw() {
  ctx.fillStyle = "#111";
  ctx.fillRect(0, 0, W, H);

  // Centre dashed line.
  ctx.fillStyle = "rgba(255,255,255,0.18)";
  for (let y = 8; y < H; y += 16) ctx.fillRect(W / 2 - 1, y, 2, 8);

  // Paddles.
  ctx.fillStyle = "#fff";
  ctx.fillRect(16, state.left.y, PADDLE_W, PADDLE_H);
  ctx.fillRect(W - 16 - PADDLE_W, state.right.y, PADDLE_W, PADDLE_H);

  // Ball.
  ctx.beginPath();
  ctx.arc(state.ball.x, state.ball.y, BALL, 0, Math.PI * 2);
  ctx.fillStyle = "#8347ff";
  ctx.fill();

  // Score.
  ctx.font = "bold 32px ui-monospace, monospace";
  ctx.textAlign = "center";
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.fillText(state.left.score, W / 2 - 40, 40);
  ctx.fillText(state.right.score, W / 2 + 40, 40);

  if (state.winner) {
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.font = "bold 22px ui-monospace, monospace";
    ctx.fillText(`${state.winner}, press space to play again`, W / 2, H / 2);
  }
}

let last = performance.now();
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  tick(dt);
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
