import * as THREE from 'https://cdn.skypack.dev/three@0.133.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.skypack.dev/three@0.133.0/examples/jsm/loaders/GLTFLoader.js';

const canvas = document.getElementById('threejsCanvas');

// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0.1);
camera.position.z = 30;

// Load pumpkin model
const pumpkins = [];

function initPumpkins() {
	// Use the GLTFLoader imported from the module build
	const loader = new GLTFLoader();
	
	loader.load('pumpkin.glb', (gltf) => {
		const pumpkinModel = gltf.scene;
		pumpkinModel.scale.set(2, 2, 2);
		
		// Spawn ~20 pumpkins
		for (let i = 0; i < 20; i++) {
			const pumpkin = pumpkinModel.clone();
			const s = 0.02+ Math.random() * 0.1;
            pumpkin.scale.set(s, s, s);

			pumpkin.position.set(
				(Math.random() - 0.5) * 80,
				(Math.random() - 0.5) * 80,
				(Math.random() - 0.5) * 1
			);
			
			pumpkin.rotation.set(
				Math.random() * Math.PI,
				Math.random() * Math.PI,
				Math.random() * Math.PI
			);
			
			pumpkin.rotationVelocity = {
				x: (Math.random() - 0.5) * 0.005,
				y: (Math.random() - 0.5) * 0.005,
				z: (Math.random() - 0.5) * 0.005
			};
			
			scene.add(pumpkin);
			pumpkins.push(pumpkin);
		}
		console.log('Pumpkins loaded:', pumpkins.length);
	}, undefined, (error) => {
		console.error('Error loading pumpkin model:', error);
	});
}

// Wait for loader to be available / initialize pumpkins
initPumpkins();

// Add lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambientLight);

const pointLight = new THREE.PointLight(0x9cf5e1, 1, 100);
pointLight.position.set(10, 10, 10);
scene.add(pointLight);

// Handle window resize
window.addEventListener('resize', () => {
	camera.aspect = window.innerWidth / window.innerHeight;
	camera.updateProjectionMatrix();
	renderer.setSize(window.innerWidth, window.innerHeight);
});

// Animation loop
function animate() {
	requestAnimationFrame(animate);
	
	// Rotate pumpkins slowly
	pumpkins.forEach(pumpkin => {
		pumpkin.rotation.x += pumpkin.rotationVelocity.x;
		pumpkin.rotation.y += pumpkin.rotationVelocity.y;
		pumpkin.rotation.z += pumpkin.rotationVelocity.z;
	});
	
	renderer.render(scene, camera);
}

animate();
