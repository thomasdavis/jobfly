import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { flyModel, poopModel, seeded } from "./objects";
import type { Job, State } from "../types";

export function createHabitat(
  canvas: HTMLCanvasElement,
  jobs: Job[],
  onSelect: (id: string) => void,
  labels: HTMLDivElement,
) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2("#211e2b", 0.023);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(13, 16, 18);
  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 0, 0);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 13;
  controls.maxDistance = 34;
  controls.maxPolarAngle = Math.PI * 0.46;
  scene.add(new THREE.HemisphereLight("#dfd2ff", "#39372c", 2));
  const sun = new THREE.DirectionalLight("#f0c69e", 3.3);
  sun.position.set(-6, 12, 5);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -11;
  sun.shadow.camera.right = 11;
  sun.shadow.camera.top = 11;
  sun.shadow.camera.bottom = -11;
  sun.shadow.normalBias = 0.04;
  scene.add(sun);
  const rim = new THREE.DirectionalLight("#a498ff", 2.4);
  rim.position.set(7, 6, -8);
  scene.add(rim);
  const ground = new THREE.Mesh(
    new THREE.CylinderGeometry(8.8, 8.1, 0.8, 96),
    new THREE.MeshStandardMaterial({ color: "#55534c", roughness: 0.95 }),
  );
  ground.position.y = -0.45;
  ground.receiveShadow = true;
  scene.add(ground);
  const lower = new THREE.Mesh(
    new THREE.CylinderGeometry(8.15, 7.7, 0.3, 96),
    new THREE.MeshStandardMaterial({ color: "#29232d", roughness: 0.7 }),
  );
  lower.position.y = -1;
  scene.add(lower);
  const rimRing = new THREE.Mesh(
    new THREE.TorusGeometry(8.65, 0.025, 6, 128),
    new THREE.MeshStandardMaterial({
      color: "#aaa18c",
      metalness: 0.5,
      roughness: 0.3,
    }),
  );
  rimRing.rotation.x = Math.PI / 2;
  scene.add(rimRing);
  const rng = seeded(71),
    dummy = new THREE.Object3D();
  const grass = new THREE.InstancedMesh(
    new THREE.ConeGeometry(0.024, 0.16, 3),
    new THREE.MeshStandardMaterial({ color: "#a5a589", roughness: 1 }),
    1500,
  );
  for (let i = 0; i < 1500; i++) {
    const a = rng() * Math.PI * 2,
      r = Math.sqrt(rng()) * 8.4;
    dummy.position.set(Math.cos(a) * r, 0.035, Math.sin(a) * r);
    dummy.rotation.set(rng() * 0.5, rng() * 6.28, rng() * 0.5);
    dummy.scale.setScalar(0.4 + rng());
    dummy.updateMatrix();
    grass.setMatrixAt(i, dummy.matrix);
  }
  scene.add(grass);
  const stones = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(0.13, 0),
    new THREE.MeshStandardMaterial({ color: "#777267", roughness: 1 }),
    90,
  );
  for (let i = 0; i < 90; i++) {
    const a = rng() * 6.28,
      r = Math.sqrt(rng()) * 8.3;
    dummy.position.set(Math.cos(a) * r, 0.02, Math.sin(a) * r);
    dummy.rotation.set(rng() * 3, rng() * 3, 0);
    dummy.scale.set(0.6 + rng(), 0.2 + rng() * 0.3, 0.7 + rng());
    dummy.updateMatrix();
    stones.setMatrixAt(i, dummy.matrix);
  }
  scene.add(stones);
  const roots: THREE.Group[] = [];
  const tags: HTMLButtonElement[] = [];
  jobs.forEach((job, i) => {
    const pile = poopModel(i);
    pile.position.set(job.x, 0, job.z);
    pile.userData.id = job.id;
    scene.add(pile);
    roots.push(pile);
    const tag = document.createElement("button");
    tag.className = "world-label";
    tag.textContent = job.company;
    tag.setAttribute("aria-label", `Inspect ${job.title} at ${job.company}`);
    tag.onclick = () => onSelect(job.id);
    labels.append(tag);
    tags.push(tag);
  });
  const fly = flyModel();
  fly.position.set(0, 0.7, 0);
  scene.add(fly);
  const halo = new THREE.Mesh(
    new THREE.RingGeometry(0.42, 0.46, 48),
    new THREE.MeshBasicMaterial({
      color: "#e9c79b",
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8,
    }),
  );
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = 0.04;
  scene.add(halo);
  const trailPositions = new Float32Array(240 * 3);
  const trailGeometry = new THREE.BufferGeometry();
  trailGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(trailPositions, 3),
  );
  trailGeometry.setDrawRange(0, 0);
  const trail = new THREE.Line(
    trailGeometry,
    new THREE.LineBasicMaterial({
      color: "#d8b790",
      transparent: true,
      opacity: 0.44,
    }),
  );
  trail.frustumCulled = false;
  scene.add(trail);
  let trailCount = 0,
    lastRevision = -1,
    frame = 0,
    state: State | null = null,
    selected: string | null = null;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const observer = new ResizeObserver(() => {
    const { width, height } = canvas.getBoundingClientRect();
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  observer.observe(canvas);
  const vector = new THREE.Vector3();
  function render() {
    frame = requestAnimationFrame(render);
    if (document.hidden) return;
    controls.update();
    if (state) {
      fly.position.x = THREE.MathUtils.lerp(fly.position.x, state.fly.x, 0.25);
      fly.position.z = THREE.MathUtils.lerp(fly.position.z, state.fly.z, 0.25);
      fly.rotation.y = state.fly.heading;
      fly.position.y = state.landed?.length
        ? 0.9
        : 0.7 + (reduced ? 0 : Math.sin(performance.now() * 0.004) * 0.04);
      for (const side of [-1, 1]) {
        const wing = fly.getObjectByName(`wing${side}`);
        if (wing)
          wing.rotation.z =
            state.running && !state.landed && !reduced
              ? Math.sin(performance.now() * 0.08) * 0.3 * side
              : 0.08 * side;
      }
      halo.position.set(fly.position.x, 0.03, fly.position.z);
      if (state.elapsed !== lastRevision) {
        lastRevision = state.elapsed;
        if (trailCount >= 240) {
          trailPositions.copyWithin(0, 3);
          trailCount = 239;
        }
        trailPositions.set(
          [fly.position.x, 0.035, fly.position.z],
          trailCount * 3,
        );
        trailCount++;
        trailGeometry.setDrawRange(0, trailCount);
        trailGeometry.attributes.position.needsUpdate = true;
      }
    }
    roots.forEach((root, i) => {
      const ring = root.getObjectByName("ring") as THREE.Mesh;
      const mat = ring.material as THREE.MeshBasicMaterial;
      const active = jobs[i].id === state?.target;
      mat.opacity = active ? 0.9 : 0.24;
      mat.color.set(
        state?.marks[jobs[i].id] === "liked"
          ? "#a7d1b8"
          : active
            ? "#f0ca9e"
            : "#b4a1db",
      );
      vector.set(root.position.x, 1.05, root.position.z).project(camera);
      const x = (vector.x * 0.5 + 0.5) * canvas.clientWidth,
        y = (-vector.y * 0.5 + 0.5) * canvas.clientHeight;
      tags[i].style.transform =
        `translate(-50%, -100%) translate(${x}px,${y}px)`;
      tags[i].classList.toggle("active", active || jobs[i].id === selected);
      tags[i].classList.toggle("liked", state?.marks[jobs[i].id] === "liked");
      tags[i].style.visibility = vector.z > 1 ? "hidden" : "visible";
    });
    renderer.render(scene, camera);
  }
  render();
  return {
    update(s: State, id: string | null) {
      state = s;
      selected = id;
    },
    resetCamera() {
      camera.position.set(13, 16, 18);
      controls.target.set(0, 0, 0);
    },
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      tags.forEach((t) => t.remove());
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Line) {
          obj.geometry.dispose();
          const materials = Array.isArray(obj.material)
            ? obj.material
            : [obj.material];
          materials.forEach((m) => m.dispose());
        }
      });
      renderer.dispose();
    },
  };
}
