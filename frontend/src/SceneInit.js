// Importing libraries needed for using ThreeJS and for the controls (zoom and pan) 
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

export default class SceneInit {
  constructor(canvasId) {
    // Core components of the scene
    this.scene = undefined;
    this.camera = undefined;
    this.renderer = undefined;

    // Camera parameters;
    this.fov = 45;
    this.nearPlane = 1;
    this.farPlane = 1000;
    this.canvasId = canvasId;

    this.controls = undefined;
  }

  initialize() {
    const aspect = window.innerWidth / window.innerHeight;
    const frustumSize = 100;

    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(
        (frustumSize * aspect) / -2, 
        (frustumSize * aspect) / 2,  
        frustumSize / 2,             
        frustumSize / -2,            
        -1000,                       
        1000                         
    );

    this.camera.position.z = 1;
    this.camera.lookAt(0, 0, 0);

    // Specify a canvas created in the HTML.
    const canvas = document.getElementById(this.canvasId);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setClearColor(0xffffff, 1);

    // Create the controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);

    this.controls.enableRotate = false;  // Rotation disables due to 2D space 

    this.controls.enableZoom = true; 
    this.controls.enablePan = true;
    this.controls.screenSpacePanning = true;

    this.controls.zoomSpeed = 0.5;
    this.controls.panSpeed = 0.8;

    this.controls.target.set(0, 0, 0); 
    
    this.controls.mouseButtons = {
      LEFT: THREE.MOUSE.PAN, 
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE
    };

    // To correct for Window resizing
    window.addEventListener('resize', () => this.onWindowResize(), false);

  }

  animate() {
    window.requestAnimationFrame(this.animate.bind(this));
    this.render();
    this.controls.update();
  }

  render() {
    // Update data on each render.
    this.renderer.render(this.scene, this.camera);
  }

  onWindowResize() {
    const aspect = window.innerWidth / window.innerHeight;
    const frustumSize = 100;
    this.camera.left = (frustumSize * aspect) / -2;
    this.camera.right = (frustumSize * aspect) / 2;
    this.camera.top = frustumSize / 2;
    this.camera.bottom = frustumSize / -2;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }
}
