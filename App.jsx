import { useEffect, useState, useRef } from 'react';
import * as THREE from 'three';
import SceneInit from './SceneInit';

function App() {
  const [networkData, setNetworkData] = useState(null);
  const [loading, setLoading] = useState(false);
  const sceneRef = useRef(null);

  // Initialize the Three.js scene once
  useEffect(() => {
    sceneRef.current = new SceneInit('myThreeJsCanvas');
    sceneRef.current.initialize();
    sceneRef.current.animate();
  }, []);

  // Fetch network data from backend
  const handleUpload = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/main', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_path: 'panda.jpg' }),
      });

      const data = await response.json();
      console.log('Backend response:', data);
      setNetworkData(data);
    } catch (err) {
      console.error('Error fetching network data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Render neurons and edges when networkData changes
  useEffect(() => {
    if (!networkData || !sceneRef.current) return;

    const { scene } = sceneRef.current;

    // Clear old objects before drawing new ones
    while (scene.children.length > 0) {
      scene.remove(scene.children[0]);
    }

    // Compute bounds for fitting the network 
    const allPositions = networkData.neuron_positions.map(([pos]) => pos).concat(networkData["edge positions"].flatMap(([s,e]) => [s, e]));
    const xs = allPositions.map(p => p[0]);
    const ys = allPositions.map(p => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const width = Math.max(1e-6, maxX - minX);
    const height = Math.max(1e-6, maxY - minY);

    // target size in scene units (should be a bit smaller than frustumSize)
    const targetSize = 80;
    const scale = targetSize / Math.max(width, height);
    const offsetX = (minX + maxX) / 2;
    const offsetY = (minY + maxY) / 2;

    // Draw edges
    networkData["edge positions"].forEach(([start, end, color]) => {
      const material = new THREE.LineBasicMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        opacity: color[3],
        transparent: true,
      });
      const points = [
        new THREE.Vector3((start[0] - offsetX) * scale, (start[1]- offsetY) * scale, 0),
        new THREE.Vector3((end[0] - offsetX) * scale, (end[1] - offsetY) * scale, 0),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, material);
      scene.add(line);
    });

    // Draw neurons as polygons (octagons) for better visibility
    const sides = 8; // for the octagon
    const radius = 0.015; // can be adjusted for size

    networkData.neuron_positions.forEach(([pos, color]) => {
      const geometry = new THREE.CircleGeometry(radius, sides);
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        opacity: color[3],
        transparent: true,
      });
      
      const neuron = new THREE.Mesh(geometry, material);
      neuron.position.set((pos[0] - offsetX) * scale, (pos[1] - offsetY) * scale, 0);
      scene.add(neuron);
    });

    // Fit the camera to the network so it is instantly visible
    if (typeof sceneRef.current.fitToScene === 'function') {
      sceneRef.current.fitToScene(1.15);
    }

  }, [networkData]);

  return (
    <div>
      <div style={{ marginBottom: '10px' }}>
        <button onClick={handleUpload} disabled={loading}>
          {loading ? 'Loading...' : 'Load panda.jpg'}
        </button>
      </div>

      <canvas id="myThreeJsCanvas" />
    </div>
  );
}

export default App;
