import * as THREE from "three";

const canvas = document.getElementById("scene");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0b18);
scene.fog = new THREE.Fog(0x0b0b18, 12, 36);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 4.5, 11);
camera.lookAt(0, 1.2, 0);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Floor.
const floor = new THREE.Mesh(
  new THREE.CircleGeometry(8, 64),
  new THREE.MeshStandardMaterial({ color: 0x2f2b43, roughness: 0.9 })
);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// Ambient + key light.
scene.add(new THREE.AmbientLight(0xffffff, 0.25));
const key = new THREE.DirectionalLight(0xffffff, 0.6);
key.position.set(4, 10, 6);
scene.add(key);

// Six columns arranged in a circle.
const COLUMN_COUNT = 6;
const RADIUS = 4.5;
const columns = [];
for (let i = 0; i < COLUMN_COUNT; i++) {
  const angle = (i / COLUMN_COUNT) * Math.PI * 2;
  const x = Math.cos(angle) * RADIUS;
  const z = Math.sin(angle) * RADIUS;
  const mat = new THREE.MeshStandardMaterial({
    color: 0x8347ff,
    emissive: 0x8347ff,
    emissiveIntensity: 0.3,
    roughness: 0.4
  });
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(0.3, 0.3, 3.4, 24),
    mat
  );
  mesh.position.set(x, 1.7, z);
  mesh.userData.baseEmissive = 0.3;
  mesh.userData.pulse = 0;
  scene.add(mesh);
  columns.push(mesh);

  const halo = new THREE.PointLight(0x8347ff, 0.6, 6);
  halo.position.copy(mesh.position);
  halo.position.y += 0.5;
  scene.add(halo);
  mesh.userData.halo = halo;
}

// Click handling: cast a ray, pulse the hit column.
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
canvas.addEventListener("click", (e) => {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(columns)[0];
  if (hit) hit.object.userData.pulse = 1.0;
});

// Drag-to-orbit (simple). Hold mouse, move horizontally.
let dragging = false;
let lastX = 0;
let yaw = 0;
canvas.addEventListener("pointerdown", (e) => {
  dragging = true;
  lastX = e.clientX;
});
canvas.addEventListener("pointerup", () => (dragging = false));
canvas.addEventListener("pointerleave", () => (dragging = false));
canvas.addEventListener("pointermove", (e) => {
  if (!dragging) return;
  yaw += (e.clientX - lastX) * 0.005;
  lastX = e.clientX;
});

// Auto-pulse a random column every 1.5 seconds so the scene breathes.
setInterval(() => {
  const i = Math.floor(Math.random() * columns.length);
  columns[i].userData.pulse = Math.max(columns[i].userData.pulse, 0.7);
}, 1500);

const clock = new THREE.Clock();
function tick() {
  const dt = clock.getDelta();
  for (const c of columns) {
    c.userData.pulse = Math.max(0, c.userData.pulse - dt * 1.2);
    const intensity = c.userData.baseEmissive + c.userData.pulse * 1.5;
    c.material.emissiveIntensity = intensity;
    c.userData.halo.intensity = 0.6 + c.userData.pulse * 1.6;
  }
  // Auto-rotate slowly when not dragging, otherwise yaw follows the drag.
  const angleNow = yaw + clock.elapsedTime * 0.05;
  camera.position.x = Math.sin(angleNow) * 11;
  camera.position.z = Math.cos(angleNow) * 11;
  camera.lookAt(0, 1.4, 0);

  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
tick();
