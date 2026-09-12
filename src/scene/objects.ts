import * as THREE from "three";

export function flyModel() {
  const fly = new THREE.Group();
  const shell = new THREE.MeshStandardMaterial({
    color: "#42364e",
    metalness: 0.72,
    roughness: 0.28,
  });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.19, 12, 8), shell);
  body.scale.set(0.8, 0.75, 1.55);
  body.position.z = -0.12;
  fly.add(body);
  const thorax = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), shell);
  thorax.position.z = 0.12;
  fly.add(thorax);
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 10, 8),
      new THREE.MeshStandardMaterial({
        color: "#cb6456",
        roughness: 0.25,
        metalness: 0.3,
      }),
    );
    eye.position.set(side * 0.105, 0.015, 0.26);
    fly.add(eye);
    const wing = new THREE.Mesh(
      new THREE.SphereGeometry(1, 12, 8),
      new THREE.MeshStandardMaterial({
        color: "#e4d8f8",
        transparent: true,
        opacity: 0.54,
        roughness: 0.15,
        metalness: 0.1,
        side: THREE.DoubleSide,
      }),
    );
    wing.scale.set(0.16, 0.013, 0.43);
    wing.position.set(side * 0.29, 0.12, -0.07);
    wing.rotation.y = side * -0.55;
    wing.name = `wing${side}`;
    fly.add(wing);
    for (let leg = 0; leg < 3; leg++) {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(side * 0.1, -0.06, (leg - 1) * 0.14),
        new THREE.Vector3(side * 0.27, -0.14, (leg - 1) * 0.23),
        new THREE.Vector3(side * 0.34, -0.26, (leg - 1) * 0.3),
      ]);
      fly.add(
        new THREE.Mesh(
          new THREE.TubeGeometry(curve, 8, 0.013, 5, false),
          shell,
        ),
      );
    }
  }
  fly.scale.setScalar(1.55);
  return fly;
}

export function poopModel(index: number) {
  const group = new THREE.Group();
  const points: THREE.Vector3[] = [];
  for (let i = 0; i <= 96; i++) {
    const t = i / 96,
      angle = t * Math.PI * 5.5;
    const r = 0.4 * (1 - t) + 0.025;
    points.push(
      new THREE.Vector3(
        Math.cos(angle) * r,
        0.15 + t * 0.66,
        Math.sin(angle) * r,
      ),
    );
  }
  const curve = new THREE.CatmullRomCurve3(points);
  const material = new THREE.MeshStandardMaterial({
    color: index % 2 ? "#a17b65" : "#886557",
    roughness: 0.8,
  });
  const pile = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 96, 0.145, 10, false),
    material,
  );
  pile.castShadow = true;
  pile.receiveShadow = true;
  group.add(pile);
  const base = new THREE.Mesh(new THREE.SphereGeometry(0.46, 20, 12), material);
  base.scale.y = 0.38;
  base.position.y = 0.12;
  base.castShadow = true;
  group.add(base);
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.68, 0.7, 64),
    new THREE.MeshBasicMaterial({
      color: "#b4a1db",
      transparent: true,
      opacity: 0.32,
      side: THREE.DoubleSide,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.025;
  ring.name = "ring";
  group.add(ring);
  return group;
}

export function seeded(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
