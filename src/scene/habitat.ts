import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { flyModel, seeded } from "./objects";
import { bakePile, distantSprites } from "./lod";
import type { Job, State } from "../types";

export function createHabitat(
  canvas: HTMLCanvasElement,
  jobs: Job[],
  onSelect: (id: string) => void,
  labels: HTMLDivElement,
) {
  const radius = Math.max(8, Math.sqrt(jobs.length) * 1.15);
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.25));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog("#f1f1ed", radius * 3, radius * 6);
  const camera = new THREE.PerspectiveCamera(43, 1, 0.1, radius * 8);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.minDistance = 5;
  controls.maxDistance = radius * 3.8;
  controls.maxPolarAngle = Math.PI * 0.47;
  controls.screenSpacePanning = false;
  function resetCamera() {
    camera.position.set(radius * 1.05, radius * 1.35, radius * 1.25);
    controls.target.set(0, 0, 0);
  }
  resetCamera();
  scene.add(new THREE.HemisphereLight("#ffffff", "#a4aa87", 2.5));
  const sun = new THREE.DirectionalLight("#fff0d8", 3);
  sun.position.set(-30, 50, 20);
  scene.add(sun);
  const rim = new THREE.DirectionalLight("#dad8fc", 2);
  rim.position.set(20, 12, -20);
  scene.add(rim);
  const ground = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius * 0.99, 1.2, 96),
    new THREE.MeshLambertMaterial({ color: "#a7b58c" }),
  );
  ground.position.y = -0.7;
  scene.add(ground);
  const edge = new THREE.Mesh(
    new THREE.TorusGeometry(radius * 0.994, 0.05, 5, 128),
    new THREE.MeshLambertMaterial({ color: "#afb699" }),
  );
  edge.rotation.x = Math.PI / 2;
  edge.position.y = -0.05;
  scene.add(edge);
  const dummy = new THREE.Object3D(),
    rng = seeded(71),
    color = new THREE.Color();
  const grass = new THREE.InstancedMesh(
    new THREE.ConeGeometry(0.05, 0.3, 3),
    new THREE.MeshLambertMaterial({ color: "#82966c" }),
    4000,
  );
  for (let i = 0; i < grass.count; i++) {
    const angle = rng() * Math.PI * 2,
      r = Math.sqrt(rng()) * radius * 0.98;
    dummy.position.set(Math.cos(angle) * r, 0.02, Math.sin(angle) * r);
    dummy.rotation.set(rng() * 0.4, rng() * 6.28, 0);
    dummy.scale.setScalar(0.4 + rng());
    dummy.updateMatrix();
    grass.setMatrixAt(i, dummy.matrix);
  }
  scene.add(grass);
  // All jobs remain rendered in two GPU instances, without per-job DOM trees.
  const profile = [
    [0, 0],
    [0.39, 0.02],
    [0.47, 0.15],
    [0.39, 0.29],
    [0.26, 0.3],
    [0.34, 0.42],
    [0.3, 0.54],
    [0.16, 0.58],
    [0.21, 0.68],
    [0.12, 0.83],
    [0, 0.99],
  ].map(([r, y]) => new THREE.Vector2(r, y));
  const piles = new THREE.InstancedMesh(
    new THREE.LatheGeometry(profile, 8),
    new THREE.MeshLambertMaterial({}),
    jobs.length,
  );
  const rings = new THREE.InstancedMesh(
    new THREE.RingGeometry(0.64, 0.71, 16),
    new THREE.MeshBasicMaterial({
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65,
    }),
    jobs.length,
  );
  jobs.forEach((job, i) => {
    dummy.position.set(job.x, 0, job.z);
    dummy.rotation.set(0, i * 2.4, 0);
    dummy.scale.setScalar(1);
    dummy.updateMatrix();
    piles.setMatrixAt(i, dummy.matrix);
    piles.setColorAt(i, color.set(i % 2 ? "#9c7860" : "#ad8b70"));
    dummy.position.y = 0.025;
    dummy.rotation.x = -Math.PI / 2;
    dummy.updateMatrix();
    rings.setMatrixAt(i, dummy.matrix);
    rings.setColorAt(i, color.set("#bcc5a9"));
  });
  piles.computeBoundingSphere();
  scene.add(piles, rings);
  const pileSprite = bakePile(renderer, piles.geometry);
  const distantJobs = distantSprites(jobs.length, false, pileSprite.texture),
    distantFlies = distantSprites(24, true);
  jobs.forEach((j, i) => {
    distantJobs.geometry.attributes.position.setXYZ(i, j.x, 0.5, j.z);
    color.set(i % 2 ? "#9c7860" : "#ad8b70");
    distantJobs.geometry.attributes.color.setXYZ(i, color.r, color.g, color.b);
  });
  scene.add(distantJobs.points, distantFlies.points);
  let nearJobs: number[] = [];
  piles.count = rings.count = 0;
  const marker = new THREE.Mesh(
    new THREE.RingGeometry(0.8, 0.87, 32),
    new THREE.MeshBasicMaterial({ color: "#684693", side: THREE.DoubleSide }),
  );
  marker.rotation.x = -Math.PI / 2;
  marker.visible = false;
  scene.add(marker);
  const template = flyModel();
  template.updateMatrixWorld(true);
  const parts: {
    mesh: THREE.InstancedMesh;
    local: THREE.Matrix4;
    wing: number;
  }[] = [];
  template.traverse((obj) => {
    if (obj instanceof THREE.Mesh) {
      const mesh = new THREE.InstancedMesh(obj.geometry, obj.material, 24);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.frustumCulled = false;
      parts.push({
        mesh,
        local: obj.matrixWorld.clone(),
        wing: obj.name.startsWith("wing") ? Number(obj.name.slice(4)) : 0,
      });
      scene.add(mesh);
    }
  });
  const bodies = Array.from({ length: 24 }, () => new THREE.Object3D());
  let state: State | null = null,
    selected: string | null = null,
    frame = 0,
    initialized = false;
  let lastTime = performance.now(),
    measuredAt = lastTime,
    frames = 0;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const matrix = new THREE.Matrix4(),
    flap = new THREE.Matrix4(),
    vector = new THREE.Vector3();
  const tags = Array.from({ length: 12 }, () => {
    const el = document.createElement("button");
    el.className = "world-label";
    el.hidden = true;
    labels.append(el);
    return el;
  });
  let labelIndices: number[] = [],
    labelsAt = 0;
  const raycaster = new THREE.Raycaster(),
    pointer = new THREE.Vector2();
  let down = [0, 0];
  function pointerDown(e: PointerEvent) {
    down = [e.clientX, e.clientY];
  }
  function pointerUp(e: PointerEvent) {
    if (Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
    const rect = canvas.getBoundingClientRect();
    pointer.set(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      (-(e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObject(piles)[0];
    if (hit?.instanceId !== undefined) {
      onSelect(jobs[nearJobs[hit.instanceId]].id);
      return;
    }
    raycaster.params.Points.threshold = 0.6;
    const far = raycaster.intersectObject(distantJobs.points)[0];
    if (far?.index !== undefined) onSelect(jobs[far.index].id);
  }
  canvas.addEventListener("pointerdown", pointerDown);
  canvas.addEventListener("pointerup", pointerUp);
  const observer = new ResizeObserver(() => {
    const { width, height } = canvas.getBoundingClientRect();
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(1, height);
    camera.updateProjectionMatrix();
  });
  observer.observe(canvas);
  function render() {
    frame = requestAnimationFrame(render);
    const now = performance.now(),
      dt = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    if (document.hidden) {
      measuredAt = now;
      frames = 0;
      return;
    }
    controls.update();
    const swarm = state?.swarm || [];
    let nearFlyCount = 0;
    parts.forEach((p) => {
      p.mesh.visible = swarm.length > 0;
    });
    swarm.forEach((fly, i) => {
      if (i >= bodies.length) return;
      const body = bodies[i],
        smooth = initialized && !reduced ? 1 - Math.exp(-dt * 1.8) : 1;
      body.position.x = THREE.MathUtils.lerp(body.position.x, fly.x, smooth);
      body.position.z = THREE.MathUtils.lerp(body.position.z, fly.z, smooth);
      body.position.y = THREE.MathUtils.lerp(
        body.position.y,
        fly.landed ? 1.12 : 1.8,
        smooth,
      );
      body.rotation.y +=
        Math.atan2(
          Math.sin(fly.heading - body.rotation.y),
          Math.cos(fly.heading - body.rotation.y),
        ) * smooth;
      body.updateMatrix();
      distantFlies.geometry.attributes.position.setXYZ(
        i,
        body.position.x,
        body.position.y,
        body.position.z,
      );
      if (camera.position.distanceTo(body.position) >= 24) return;
      const renderIndex = nearFlyCount++;
      parts.forEach((part) => {
        matrix.multiplyMatrices(body.matrix, part.local);
        if (part.wing && state?.running && !fly.landed && !reduced) {
          flap.makeRotationZ(Math.sin(now * 0.075 + i) * 0.22 * part.wing);
          matrix.multiply(flap);
        }
        part.mesh.setMatrixAt(renderIndex, matrix);
      });
    });
    if (swarm.length) initialized = true;
    distantFlies.geometry.attributes.position.needsUpdate = true;
    distantFlies.geometry.setDrawRange(0, swarm.length);
    distantJobs.material.uniforms.pixelScale.value =
      distantFlies.material.uniforms.pixelScale.value =
        (canvas.clientHeight * renderer.getPixelRatio()) /
        (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    parts.forEach((p) => {
      p.mesh.count = nearFlyCount;
      p.mesh.instanceMatrix.needsUpdate = true;
    });
    if (now - labelsAt > 300) {
      labelsAt = now;
      const distances = jobs.map(
        (j) =>
          (j.x - camera.position.x) ** 2 +
          (j.z - camera.position.z) ** 2 +
          (camera.position.y - 0.5) ** 2,
      );
      nearJobs = [...jobs.keys()]
        .filter((i) => distances[i] < 24 ** 2)
        .sort((a, b) => distances[a] - distances[b])
        .slice(0, 200);
      const cutoff =
        nearJobs.length === 200
          ? Math.sqrt(distances[nearJobs[199]]) + 0.0001
          : 24;
      distantJobs.material.uniforms.nearCutoff.value = cutoff;
      piles.count = rings.count = nearJobs.length;
      nearJobs.forEach((index, i) => {
        const j = jobs[index];
        dummy.position.set(j.x, 0, j.z);
        dummy.rotation.set(0, index * 2.4, 0);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
        piles.setMatrixAt(i, dummy.matrix);
        piles.setColorAt(i, color.set(index % 2 ? "#9c7860" : "#ad8b70"));
        dummy.position.y = 0.025;
        dummy.rotation.x = -Math.PI / 2;
        dummy.updateMatrix();
        rings.setMatrixAt(i, dummy.matrix);
        const activity = state?.ecosystem?.activity[j.id];
        rings.setColorAt(
          i,
          color.set(
            state?.marks[j.id] === "liked"
              ? "#307c53"
              : activity?.mature
                ? "#7955af"
                : activity
                  ? "#c29441"
                  : "#bcc5a9",
          ),
        );
      });
      piles.instanceMatrix.needsUpdate =
        rings.instanceMatrix.needsUpdate = true;
      if (piles.instanceColor) piles.instanceColor.needsUpdate = true;
      if (rings.instanceColor) rings.instanceColor.needsUpdate = true;
      const priority = new Set([
        selected,
        ...(state?.ecosystem?.recommendations || []).slice(0, 4),
      ]);
      const close = [...jobs.keys()].sort(
        (a, b) =>
          (jobs[a].x - controls.target.x) ** 2 +
          (jobs[a].z - controls.target.z) ** 2 -
          ((jobs[b].x - controls.target.x) ** 2 +
            (jobs[b].z - controls.target.z) ** 2),
      );
      labelIndices = [
        ...new Set(
          [...jobs.keys()]
            .filter((i) => priority.has(jobs[i].id))
            .concat(
              camera.position.distanceTo(controls.target) < radius
                ? close.slice(0, 8)
                : [],
            ),
        ),
      ].slice(0, tags.length);
    }
    tags.forEach((tag, i) => {
      const index = labelIndices[i];
      if (index === undefined) {
        tag.hidden = true;
        return;
      }
      const job = jobs[index];
      vector.set(job.x, 1.5, job.z).project(camera);
      tag.hidden =
        vector.z > 1 ||
        vector.z < -1 ||
        Math.abs(vector.x) > 0.95 ||
        Math.abs(vector.y) > 0.9;
      tag.textContent = job.company;
      tag.setAttribute("aria-label", `Inspect ${job.title} at ${job.company}`);
      tag.onclick = () => onSelect(job.id);
      tag.style.transform = `translate(-50%,-100%) translate(${(vector.x * 0.5 + 0.5) * canvas.clientWidth}px,${(-vector.y * 0.5 + 0.5) * canvas.clientHeight}px)`;
      tag.classList.toggle("active", selected === job.id);
    });
    renderer.render(scene, camera);
    frames++;
    if (now - measuredAt >= 1000) {
      canvas.dataset.fps = ((frames * 1000) / (now - measuredAt)).toFixed(1);
      canvas.dataset.drawCalls = String(renderer.info.render.calls);
      canvas.dataset.triangles = String(renderer.info.render.triangles);
      canvas.dataset.jobs = String(jobs.length);
      canvas.dataset.detailedJobs = String(nearJobs.length);
      canvas.dataset.flies = String(swarm.length);
      frames = 0;
      measuredAt = now;
    }
  }
  render();
  return {
    update(s: State, id: string | null) {
      const changedSelection = id !== selected;
      state = s;
      selected = id;
      const chosen = jobs.find((j) => j.id === id);
      if (changedSelection && chosen) {
        const offset = camera.position
          .clone()
          .sub(controls.target)
          .normalize()
          .multiplyScalar(16);
        controls.target.set(chosen.x, 0, chosen.z);
        camera.position.copy(controls.target).add(offset);
      }
      marker.visible = !!chosen;
      if (chosen) marker.position.set(chosen.x, 0.04, chosen.z);
      jobs.forEach((job, i) => {
        const activity = s.ecosystem?.activity[job.id];
        color.set(
          s.marks[job.id] === "liked"
            ? "#307c53"
            : activity?.mature
              ? "#7955af"
              : activity
                ? "#b89554"
                : i % 2
                  ? "#9c7860"
                  : "#ad8b70",
        );
        distantJobs.geometry.attributes.color.setXYZ(
          i,
          color.r,
          color.g,
          color.b,
        );
      });
      distantJobs.geometry.attributes.color.needsUpdate = true;
    },
    resetCamera,
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      tags.forEach((t) => t.remove());
      canvas.removeEventListener("pointerdown", pointerDown);
      canvas.removeEventListener("pointerup", pointerUp);
      const geometries = new Set<THREE.BufferGeometry>(),
        materials = new Set<THREE.Material>();
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.Points) {
          geometries.add(obj.geometry);
          (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(
            (m) => materials.add(m),
          );
          if (obj instanceof THREE.InstancedMesh) obj.dispose();
        }
      });
      geometries.forEach((g) => g.dispose());
      pileSprite.dispose();
      materials.forEach((m) => m.dispose());
      renderer.dispose();
    },
  };
}
