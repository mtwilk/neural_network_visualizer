// Importing necessary libraries and components  for the network visualization 
import { useEffect, useState, useRef } from 'react'; 
import * as THREE from 'three';
import SceneInit from './SceneInit';

function App() {
  const [labels, setLabels] = useState([]);  // Holds the top 5 classification labels 
  const [scores, setScores] = useState([]);  // Holds the top 5 confidence scores
  const [networkData, setNetworkData] = useState(null);  // Holds the network data
  const [loading, setLoading] = useState(false);  // Indicates loading state
  const [selectedImage, setSelectedImage] = useState('');  // Holds the currently selected image
  const sceneRef = useRef(null);  // Reference to the Three.js scene

  // List of available images
  const images = [
    'panda.jpg',
    'red_panda.jpg',
    'polar_bear.jpg',
    'brown_bear.jpg',
    'sun_bear.jpg',
    'beaver.jpg',
    'binturong.jpg',
    'giant_anteater.jpg'
  ];

  // Initialize the Three.js scene
  useEffect(() => {
    sceneRef.current = new SceneInit('myThreeJsCanvas');
    sceneRef.current.initialize();
    sceneRef.current.animate();
  }, []);

  // Setting parameters for the overlay displaying the classification results
  const overlayStyle = {
    position: 'fixed',
    top: '0',
    right: '0',
    background: 'black',
    padding: '10px',
    borderRadius: '5px 0 0 5px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
    zIndex: 1000,
    fontFamily: 'Arial, sans-serif',
    color: 'white' // White text for better contrast
  };

  // Fetch network data from backend - reusable function
  const loadImage = async (imagePath) => {
    setLoading(true);  // Show loading indicator
    setSelectedImage(imagePath);  // Update selected image
    try {
      // Send POST request to backend with image path
      const response = await fetch('http://localhost:5000/main', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_path: imagePath }),
      });

      // Parse JSON response and update network data state
      const data = await response.json();
      setLabels(data.labels || []);
      setScores(data.scores || []);
      console.log('Backend response:', data);
      setNetworkData(data);  // Network data is processed later 
    } catch (err) {
      console.error('Error fetching network data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Render neurons and edges when networkData changes
  useEffect(() => {
    if (!networkData || !sceneRef.current) return;

    const { scene } = sceneRef.current;  // Get the Three.js scene

    // Remove existing objects from the scene (resets it)
    while (scene.children.length > 0) {
      scene.remove(scene.children[0]);
    }

    // Find bounds of the network to center and scale it properly
    const allPositions = networkData.neuron_positions.map(([pos]) => pos).concat(networkData["edge positions"].flatMap(([s,e]) => [s, e]));
    
    // Extract x and y coordinates
    const xs = allPositions.map(p => p[0]);
    const ys = allPositions.map(p => p[1]);
    
    // Compute bounds
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    
    // Compute dimensions 
    const width = Math.max(1e-6, maxX - minX);
    const height = Math.max(1e-6, maxY - minY);

    // Determine scale to fit the network within a target size
    const targetSize = 80;  // network size in scene space (smaller than frustumSize)
    const scale = targetSize / Math.max(width, height);
    const offsetX = (minX + maxX) / 2;
    const offsetY = (minY + maxY) / 2;

    // Draw edges
    networkData["edge positions"].forEach(([start, end, color]) => {
      const material = new THREE.LineBasicMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        opacity: color[3] * 0.04,
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
    const sides = 8; // octagon
    const radius = 0.005; // can be adjusted for size

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


    // Get x coordinates of each layer to place layer labels  
    const layerMap = {};
    networkData.neuron_positions.forEach(([pos, color]) => {
      const x = Math.round(pos[0] * 100) / 100; 
      if (!layerMap[x]) layerMap[x] = [];
      layerMap[x].push({pos, color});
    })

    const layerXPositions = Object.keys(layerMap).map(Number).sort((a,b) => a - b);


    // Create sprites for layer labels
    function createTextSprite(message, parameters = {}) {
      const fontface = parameters.fontface || 'Arial';
      const fontsize = parameters.fontsize || 48;
      const borderThickness = parameters.borderThickness || 4;
      const backgroundColor = { r:255, g:255, b:255, a:0.8 }; // Semi-transparent background

      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      context.font = `${fontsize}px ${fontface}`;

      // Get text metrics for proper sizing
      const metrics = context.measureText(message);
      const textWidth = metrics.width;

      // Size canvas to fit text
      canvas.width = textWidth + borderThickness * 2;
      canvas.height = fontsize * 1.4;

      // Reset font after canvas resize
      context.font = `${fontsize}px ${fontface}`;

      // Draw background
      context.fillStyle = `rgba(${backgroundColor.r},${backgroundColor.g},${backgroundColor.b},${backgroundColor.a})`;
      context.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw text
      context.fillStyle = 'rgba(0, 0, 0, 1.0)';
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(message, canvas.width/2, canvas.height/2);

      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;

      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      
      // Scale sprite based on canvas dimensions AND font size
      // Normalize by reference font size (48) so it scales proportionally
      const baseScaleFactor = 3;
      const scaleFactor = baseScaleFactor * (fontsize / 48);
      sprite.scale.set((canvas.width / canvas.height) * scaleFactor, scaleFactor, 1);


      return sprite;
    }

    // add layer labels to the scene
    const layerLabels = ['Convolution output', 'FC1', 'FC2', 'FC3 - output'];

    // Update the layer label positioning
    layerXPositions.forEach((xPos, i) => {
      const label = layerLabels[i] || `Layer ${i+1}`;
      const sprite = createTextSprite(label, { fontsize: 44 });
      
      // Position labels above the neurons with proper scaling
      const yPos = Math.max(...layerMap[xPos].map(n => n.pos[1]));
      sprite.position.set(
        (xPos - offsetX) * scale,
        (yPos - offsetY) * scale + 2, 
        0
      );
      scene.add(sprite);

      // Add neuron count label below the layer name
      if (networkData.layer_sizes && networkData.layer_sizes[i] !== undefined) {
        const neuronCount = networkData.layer_sizes[i];
        const countLabel = `${neuronCount} neurons`;
        const countSprite = createTextSprite(countLabel, { fontsize: 28 }); // Even smaller font (was 36)
        
        countSprite.position.set(
          (xPos - offsetX) * scale,
          (yPos - offsetY) * scale + 0.10, // Position below the layer name (adjusted spacing)
          0
        );
        scene.add(countSprite);
      }
    });

     

    // Fit the camera to the network so it is instantly visible
    if (typeof sceneRef.current.fitToScene === 'function') {
      sceneRef.current.fitToScene(1.15);
    }

  }, [networkData]);

  return (
    <div>
      {/* Image selection buttons */}
      <div style={{ marginBottom: '10px' }}>
        {images.map((image) => (
          <button 
            key={image}
            onClick={() => loadImage(image)} 
            disabled={loading}
            style={{ marginRight: '5px' }}
          >
            {loading && selectedImage === image ? 'Loading...' : `Load ${image.replace('.jpg', '')}`}
          </button>
        ))}
      </div>

      {/* Display selected image - no frame, just the image */}
      {selectedImage && (
        <div style={{
          position: 'fixed',
          top: '50px',
          left: '10px',
          zIndex: 1000
        }}>
          <img 
            src={`http://localhost:5000/images/${selectedImage}`} 
            alt={selectedImage}
            style={{
              width: '200px',
              height: '200px',
              objectFit: 'cover',
              display: 'block'
            }}
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      )}

      {/* Classification results overlay */}
      {(labels.length > 0 || scores.length > 0) && (
        <div style={overlayStyle}>
          <strong>Top 5 Classification Results:</strong><br />
          {labels.map((label, index) => (
            <div key={index} style={{ marginTop: '5px' }}>
              {index + 1}. {label}: {scores[index]?.toFixed(4) || 'N/A'}
            </div>
          ))}
        </div>
      )}

      <canvas id="myThreeJsCanvas" />
    </div>
  );
}

export default App;
