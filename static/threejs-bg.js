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

// add robot holder
let robot = null;

// --- Added: mouse tracking and raycaster ---
const mouse = new THREE.Vector2(0, 0); // normalized device coords
const raycaster = new THREE.Raycaster();

function loadGLBWithFallback(loader, path, fallbackPath, onLoad, onError) {
	loader.load(path, onLoad, undefined, (error) => {
		console.warn(`Failed to load ${path}, attempting fallback: ${fallbackPath}`);
		loader.load(fallbackPath, onLoad, undefined, (fallbackError) => {
			console.error(`Failed to load fallback ${fallbackPath}:`, fallbackError);
			if (onError) onError(fallbackError);
		});
	});
}

// Wait for loader to be available / initialize eyes
// initEyse();

// --- Added: load robot model and place at center ---
{
	// create a separate loader for the robot
	const robotLoader = new GLTFLoader();
	loadGLBWithFallback(
		robotLoader,
		'static/robot.glb',
		'robot.glb',
		(gltf) => {
			robot = gltf.scene;
			// position at scene center
			robot.position.set(0, -5, 0);
			// adjust scale as needed (tweak 1..10 depending on model size)
			robot.scale.set(22, 22, 22);
			// optional: reset rotation if model contains unexpected orientation
			robot.rotation.set(0, 0, 0);
			scene.add(robot);
			console.log('robot loaded and added to scene');
		},
		(error) => {
			console.error('Error loading robot model:', error);
		}
	);
}

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

// --- Added: update mouse on move (NDC) ---
function updateMouseFromEvent(event) {
	const rect = renderer.domElement.getBoundingClientRect();
	const x = (event.clientX - rect.left) / rect.width;
	const y = (event.clientY - rect.top) / rect.height;
	mouse.x = (x * 2) - 1;
	mouse.y = -(y * 2) + 1;
}
window.addEventListener('mousemove', updateMouseFromEvent, { passive: true });
window.addEventListener('touchmove', (e) => {
	if (e.touches && e.touches.length > 0) updateMouseFromEvent(e.touches[0]);
}, { passive: true });

// Animation loop
function animate() {
	requestAnimationFrame(animate);
	
	const now = performance.now() * 0.001; // seconds
	// update ray once per frame
	raycaster.setFromCamera(mouse, camera);

	// Rotate robot around Y-axis
	if (robot) {
		robot.rotation.y += 0.001; // Adjust speed as needed
	}

	// renderer.render(scene, camera);
	renderer.render(scene, camera);
}

animate();
