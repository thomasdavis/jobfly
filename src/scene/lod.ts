import * as THREE from "three";

/** Distant objects stay represented; close objects use the detailed meshes. */
export function distantSprites(
  count: number,
  fly = false,
  spriteMap: THREE.Texture | null = null,
) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(count * 3), 3),
  );
  const colors = new Float32Array(count * 3);
  colors.fill(0.6);
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    vertexColors: true,
    uniforms: {
      pixelScale: { value: 600 },
      nearCutoff: { value: 24 },
      spriteMap: { value: spriteMap },
    },
    vertexShader: `uniform float pixelScale; uniform float nearCutoff; varying vec3 tint; varying float close;
      void main(){vec4 mv=modelViewMatrix*vec4(position,1.);close=length(mv.xyz)<nearCutoff?1.:0.;tint=color;gl_Position=projectionMatrix*mv;gl_PointSize=clamp(${fly ? "1.9" : "1.35"}*pixelScale/max(1.,-mv.z),${fly ? "6." : "2."},80.);}`,
    fragmentShader: fly
      ? `varying vec3 tint; varying float close;
      float oval(vec2 p,vec2 c,vec2 r){return length((p-c)/r);}
      void main(){if(close>.5)discard;vec2 p=gl_PointCoord;float b=oval(p,vec2(.5,.58),vec2(.12,.32));float w=min(oval(p,vec2(.26,.35),vec2(.23,.14)),oval(p,vec2(.74,.35),vec2(.23,.14)));if(min(b,w)>1.)discard;gl_FragColor=b<1.?vec4(.17,.13,.21,1.):vec4(.74,.74,.88,.85);}`
      : `uniform sampler2D spriteMap; varying vec3 tint; varying float close;
      void main(){if(close>.5)discard;vec4 tex=texture2D(spriteMap,vec2(gl_PointCoord.x,1.-gl_PointCoord.y));if(tex.a<.1)discard;gl_FragColor=vec4(tex.rgb*10.*tint,tex.a);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return { points, geometry, material };
}

/** Bake the actual pile geometry once; distant jobs keep the same shape/light. */
export function bakePile(
  renderer: THREE.WebGLRenderer,
  geometry: THREE.BufferGeometry,
) {
  const scene = new THREE.Scene();
  const material = new THREE.MeshLambertMaterial({ color: "white" });
  scene.add(new THREE.Mesh(geometry, material));
  scene.add(new THREE.HemisphereLight("#ffffff", "#a4aa87", 0.25));
  const sun = new THREE.DirectionalLight("#fff0d8", 0.3);
  sun.position.set(-30, 50, 20);
  scene.add(sun);
  const rim = new THREE.DirectionalLight("#dad8fc", 0.2);
  rim.position.set(20, 12, -20);
  scene.add(rim);
  const camera = new THREE.OrthographicCamera(
    -0.675,
    0.675,
    0.675,
    -0.675,
    0.1,
    10,
  );
  camera.position.set(1.4, 1.9, 2);
  camera.lookAt(0, 0.5, 0);
  const target = new THREE.WebGLRenderTarget(96, 96);
  const tone = renderer.toneMapping;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.setRenderTarget(target);
  renderer.clear();
  renderer.render(scene, camera);
  renderer.setRenderTarget(null);
  renderer.toneMapping = tone;
  material.dispose();
  return target;
}
