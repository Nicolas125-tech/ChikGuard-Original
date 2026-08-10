const cameras = Array.from({ length: 10000 }, (_, i) => ({
  camera_id: `cam-${i}`,
  name: `Farm ${i}`
}));

const activeCamera = 'cam-9999';
const iterations = 10000;

console.log(`Running benchmark with ${cameras.length} cameras, ${iterations} renders...`);

// Benchmark 1: Array.find
console.time('Array.find (Current)');
for (let i = 0; i < iterations; i++) {
  const farmName = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';
}
console.timeEnd('Array.find (Current)');

// Benchmark 2: Map lookup
console.time('Build Map');
const cameraMap = new Map();
cameras.forEach(c => cameraMap.set(c.camera_id, c.name));
console.timeEnd('Build Map');

console.time('Map.get (O(1))');
for (let i = 0; i < iterations; i++) {
  const farmName = cameraMap.get(activeCamera) || 'Granja Principal';
}
console.timeEnd('Map.get (O(1))');

// Benchmark 3: useMemo equivalent
console.time('Compute once (useMemo O(N) cached)');
const farmNameCached = cameras.find(c => c.camera_id === activeCamera)?.name || 'Granja Principal';
for (let i = 0; i < iterations; i++) {
  const farmName = farmNameCached;
}
console.timeEnd('Compute once (useMemo O(N) cached)');
