import * as THREE from "three";

/** Distant objects stay represented; close objects use the detailed meshes. */
export function distantSprites(count: number, fly = false) {
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
    uniforms: { pixelScale: { value: 600 }, nearCutoff: { value: 24 } },
    vertexShader: `uniform float pixelScale; uniform float nearCutoff; varying vec3 tint; varying float close;
      void main(){vec4 mv=modelViewMatrix*vec4(position,1.);close=length(mv.xyz)<nearCutoff?1.:0.;tint=color;gl_Position=projectionMatrix*mv;gl_PointSize=clamp(${fly ? "1.9" : "1.15"}*pixelScale/max(1.,-mv.z),${fly ? "6." : "2."},80.);}`,
    fragmentShader: fly
      ? `varying vec3 tint; varying float close;
      float oval(vec2 p,vec2 c,vec2 r){return length((p-c)/r);}
      void main(){if(close>.5)discard;vec2 p=gl_PointCoord;float b=oval(p,vec2(.5,.58),vec2(.12,.32));float w=min(oval(p,vec2(.26,.35),vec2(.23,.14)),oval(p,vec2(.74,.35),vec2(.23,.14)));if(min(b,w)>1.)discard;gl_FragColor=b<1.?vec4(.17,.13,.21,1.):vec4(.74,.74,.88,.85);}`
      : `varying vec3 tint; varying float close;
      float oval(vec2 p,vec2 c,vec2 r){return length((p-c)/r);}
      void main(){if(close>.5)discard;vec2 p=gl_PointCoord;float shape=min(oval(p,vec2(.5,.74),vec2(.44,.19)),min(oval(p,vec2(.48,.51),vec2(.32,.18)),oval(p,vec2(.52,.3),vec2(.18,.19))));if(shape>1.)discard;float light=.7+.4*(1.-p.x)+.16*(1.-p.y);gl_FragColor=vec4(tint*light,1.);
#include <colorspace_fragment>
}`,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return { points, geometry, material };
}
