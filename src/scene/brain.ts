import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { BrainData, State } from "../types";

export function createBrain(canvas: HTMLCanvasElement, data: BrainData) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  const scene = new THREE.Scene(),
    camera = new THREE.PerspectiveCamera(42, 1, 0.01, 30);
  camera.position.set(0.0, 0.04, 2.8);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 1;
  controls.maxDistance = 5;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(data.positions, 3),
  );
  const colors = new Float32Array(data.mapped * 3),
    strength = new Float32Array(data.mapped),
    firedAt = new Float32Array(data.mapped);
  firedAt.fill(-100);
  const palette = ["#75688c", "#b66c29", "#7042c3", "#18784f"].map(
    (c) => new THREE.Color(c),
  );
  data.classes.forEach((c, i) => {
    colors.set(palette[c].toArray(), i * 3);
    strength[i] = c === 0 ? 0.85 : 1.6;
  });
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("strength", new THREE.BufferAttribute(strength, 1));
  geometry.setAttribute("firedAt", new THREE.BufferAttribute(firedAt, 1));
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.NormalBlending,
    vertexColors: true,
    uniforms: {
      time: { value: 0 },
      pixelRatio: { value: renderer.getPixelRatio() },
    },
    vertexShader: `attribute float strength; attribute float firedAt; varying vec3 vColor; varying float vAlpha; uniform float time; uniform float pixelRatio; void main(){float fire=exp(-max(0.0,time-firedAt)*4.0);vColor=mix(color,vec3(.4,.12,.8),fire);vAlpha=strength*.28+fire*.9;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_PointSize=(1.15+fire*2.2)*pixelRatio;gl_Position=projectionMatrix*mv;}`,
    fragmentShader: `varying vec3 vColor; varying float vAlpha; void main(){float d=length(gl_PointCoord-vec2(.5));if(d>.5)discard;gl_FragColor=vec4(vColor,vAlpha*(1.0-smoothstep(.1,.5,d)));}`,
  });
  const points = new THREE.Points(geometry, material);
  scene.add(points);
  const observer = new ResizeObserver(() => {
    const { width, height } = canvas.getBoundingClientRect();
    if (!height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  observer.observe(canvas);
  let frame = 0,
    lastElapsed = -1;
  function render() {
    frame = requestAnimationFrame(render);
    if (document.hidden) return;
    material.uniforms.time.value = performance.now() / 1000;
    controls.update();
    renderer.render(scene, camera);
  }
  render();
  return {
    update(state: State) {
      if (lastElapsed === state.elapsed) return;
      lastElapsed = state.elapsed;
      const t = performance.now() / 1000;
      state.spikes.forEach((i) => {
        if (i < firedAt.length) firedAt[i] = t;
      });
      geometry.attributes.firedAt.needsUpdate = true;
    },
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    },
  };
}
