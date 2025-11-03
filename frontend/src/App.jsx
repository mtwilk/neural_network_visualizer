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

    // Draw edges
    networkData["edge positions"].forEach(([start, end, color]) => {
      const material = new THREE.LineBasicMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        opacity: color[3],
        transparent: true,
      });
      const points = [
        new THREE.Vector3(start[0], start[1], 0),
        new THREE.Vector3(end[0], end[1], 0),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, material);
      scene.add(line);
    });

    // Draw neurons
    networkData.neuron_positions.forEach(([pos, color]) => {
      const geometry = new THREE.CircleGeometry(0.015, 12);
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        opacity: color[3],
        transparent: true,
      });
      const neuron = new THREE.Mesh(geometry, material);
      neuron.position.set(pos[0], pos[1], 0);
      scene.add(neuron);
    });
  }, [networkData]);

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, overflow: 'hidden' }}>
      <div style={{ 
        position: 'absolute', 
        top: '20px', 
        left: '20px', 
        zIndex: 1000,
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '15px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <button 
          onClick={handleUpload} 
          disabled={loading}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            cursor: loading ? 'not-allowed' : 'pointer',
            background: loading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px'
          }}
        >
          {loading ? 'Loading...' : 'Load panda.jpg'}
        </button>
        {networkData && (
          <div style={{ marginTop: '10px', fontSize: '14px' }}>
            <strong>Prediction:</strong> {networkData.label}<br />
            <strong>Score:</strong> {(networkData.score * 100).toFixed(2)}%
          </div>
        )}
      </div>

      <canvas id="myThreeJsCanvas" style={{ display: 'block', width: '100%', height: '100%' }} />
    </div>
  );
}

export default App;
