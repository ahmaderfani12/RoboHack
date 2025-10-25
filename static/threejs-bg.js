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
const eyes = [];

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

function initEyse() {
	// Use the GLTFLoader imported from the module build
	const loader = new GLTFLoader();
	
	loadGLBWithFallback(
		loader,
		'static/anatomical_eye_ball.glb',
		'anatomical_eye_ball.glb',
		(gltf) => {
			const pumpkinModel = gltf.scene;
			pumpkinModel.scale.set(2, 2, 2);
			
			// Spawn ~20 eyes
			for (let i = 0; i < 20; i++) {
				const pumpkin = pumpkinModel.clone();
				const s = 0.02 + Math.random() * 0.035;
				pumpkin.scale.set(s, s, s);

				pumpkin.position.set(
					(Math.random() - 0.5) * 100,
					(Math.random() - 0.5) * 80,
					(Math.random() - 0.5) * 5 - 10
				);
				
				pumpkin.rotation.set(
					Math.random() * Math.PI,
					Math.random() * Math.PI,
					Math.random() * Math.PI
				);
				
				scene.add(pumpkin);
				
				// store per-eye base scale and tiny jelly params for subtle animation
				pumpkin.userData = pumpkin.userData || {};
				pumpkin.userData.baseScale = new THREE.Vector3(s, s, s);
				pumpkin.userData.phase = Math.random() * Math.PI * 2;
				// Very small amplitude and slow-ish frequency so effect is subtle
				pumpkin.userData.jellyAmp = 0.1 * (0.5 + Math.random() * 0.7); // ~0.015 - 0.052
				pumpkin.userData.jellyFreq = 0.8 + Math.random() * 1.6; // ~0.8 - 2.4
				
				eyes.push(pumpkin);
			}
			console.log('eyes loaded:', eyes.length);
		},
		(error) => {
			console.error('Error loading pumpkin model:', error);
		}
	);
}

// Wait for loader to be available / initialize eyes
initEyse();

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

	// per-eye lookAt + subtle jelly/squeeze scaling
	eyes.forEach(eye => {
		// small jelly/squeeze animation based on stored base scale
		const ud = eye.userData || {};
		const base = ud.baseScale || eye.scale;
		const phase = ud.phase || 0;
		const amp = ud.jellyAmp || 0.03;
		const freq = ud.jellyFreq || 1.2;

		// anisotropic factors: X vs Y opposite phase => squeeze effect,
		// Z gets a much smaller wobble to keep volume feel.
		const sX = 1 + amp * Math.sin(now * freq + phase);
		const sY = 1 - amp * Math.sin(now * freq + phase); // opposite to X
		const sZ = 1 + (amp * 0.25) * Math.sin(now * freq + phase + Math.PI / 2);

		eye.scale.set(base.x * sX, base.y * sY, base.z * sZ);

		// compute a world-space target where the camera->mouse ray intersects plane at eye.z
		const rayOrigin = raycaster.ray.origin;
		const rayDir = raycaster.ray.direction;
		const eyeZ = eye.position.z+3;

		// avoid division by near-zero if ray is parallel to plane
		if (Math.abs(rayDir.z) > 1e-6) {
			const t = (eyeZ - rayOrigin.z) / rayDir.z;
			const target = new THREE.Vector3().copy(rayDir).multiplyScalar(t).add(rayOrigin);
			eye.lookAt(target);
		}
	});
	
	renderer.render(scene, camera);
}

animate();
