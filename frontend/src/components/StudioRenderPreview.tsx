import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";

// Camera Intent (GLOSSARY.md): the preview camera state captured on Render —
// position + look-at target + FOV in three.js (Y-up) coordinates.
export interface CameraIntent {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

export interface StudioRenderPreviewHandle {
  getCameraIntent: () => CameraIntent | null;
}

// Blender's default studio angle (azimuth 45, elevation 28) expressed in
// three.js (Y-up) coordinates: blender (x,y,z) maps to three (x,z,-y).
const DEFAULT_VIEW_DIRECTION = new THREE.Vector3(0.6243, 0.4695, -0.6243).normalize();
const FRAME_MARGIN = 1.15; // matches blender_studio.py so the preview frames like the render

const extOf = (name: string) => name.slice(name.lastIndexOf(".")).toLowerCase();

// Build the preview object so it matches what Blender shows for the same file:
// STL/PLY are imported raw (Z-up) by Blender, so rotate them upright in the
// Y-up preview; Blender's OBJ importer converts Y-up -> Z-up itself, and
// three.js loads OBJ raw, so OBJ needs no rotation.
const loadModel = async (file: File): Promise<THREE.Object3D> => {
  const material = new THREE.MeshStandardMaterial({ color: "#1a1a1a", roughness: 0.3, metalness: 0 });
  const ext = extOf(file.name);
  if (ext === ".stl" || ext === ".ply") {
    const buffer = await file.arrayBuffer();
    const geometry = ext === ".stl" ? new STLLoader().parse(buffer) : new PLYLoader().parse(buffer);
    if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();
    geometry.rotateX(-Math.PI / 2);
    return new THREE.Mesh(geometry, material);
  }
  if (ext === ".obj") {
    const group = new OBJLoader().parse(await file.text());
    group.traverse((child) => {
      if (child instanceof THREE.Mesh) child.material = material;
    });
    return group;
  }
  throw new Error(`Preview is not supported for ${ext} files yet`);
};

const disposeObject = (obj: THREE.Object3D) => {
  obj.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry.dispose();
      const material = child.material;
      for (const m of Array.isArray(material) ? material : [material]) m.dispose();
    }
  });
};

type OrbitControlsImpl = React.ComponentRef<typeof OrbitControls>;

interface PreviewSceneProps {
  file: File;
  fov: number;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onReady: () => void;
  onError: (message: string) => void;
}

function PreviewScene({ file, fov, controlsRef, onReady, onError }: PreviewSceneProps) {
  const camera = useThree((s) => s.camera);
  const [model, setModel] = useState<THREE.Object3D | null>(null);
  const prevFovRef = useRef(fov);

  useEffect(() => {
    let cancelled = false;
    let loaded: THREE.Object3D | null = null;
    loadModel(file)
      .then((obj) => {
        if (cancelled) {
          disposeObject(obj);
          return;
        }
        loaded = obj;
        setModel(obj);
        // Frame the whole model from the default studio angle, mirroring the
        // render's auto-framing (bounding sphere + FOV + margin)
        const sphere = new THREE.Box3().setFromObject(obj).getBoundingSphere(new THREE.Sphere());
        const distance = (sphere.radius / Math.tan(THREE.MathUtils.degToRad(fov) / 2)) * FRAME_MARGIN;
        if (camera instanceof THREE.PerspectiveCamera) {
          camera.position.copy(sphere.center).addScaledVector(DEFAULT_VIEW_DIRECTION, distance);
          camera.near = Math.max(distance / 100, 0.0001);
          camera.far = distance * 100;
          camera.fov = fov;
          camera.updateProjectionMatrix();
          camera.lookAt(sphere.center);
        }
        controlsRef.current?.target.copy(sphere.center);
        controlsRef.current?.update();
        onReady();
      })
      .catch((err) => onError((err as Error).message || "Could not load the model preview"));
    return () => {
      cancelled = true;
      setModel(null);
      if (loaded) disposeObject(loaded);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file]);

  // FOV slider: keep the model framed by scaling the camera distance with the
  // FOV, so the slider changes perspective rather than zoom
  useEffect(() => {
    const prevFov = prevFovRef.current;
    prevFovRef.current = fov;
    if (!(camera instanceof THREE.PerspectiveCamera) || camera.fov === fov) return;
    const controls = controlsRef.current;
    if (controls) {
      const offset = camera.position.clone().sub(controls.target);
      const distance =
        (offset.length() * Math.tan(THREE.MathUtils.degToRad(prevFov) / 2)) /
        Math.tan(THREE.MathUtils.degToRad(fov) / 2);
      camera.position.copy(controls.target).addScaledVector(offset.normalize(), distance);
    }
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }, [fov, camera, controlsRef]);

  if (!model) return null;
  return <primitive object={model} />;
}

interface StudioRenderPreviewProps {
  file: File;
  fov: number;
  onReady?: () => void;
}

const StudioRenderPreview = forwardRef<StudioRenderPreviewHandle, StudioRenderPreviewProps>(
  ({ file, fov, onReady }, ref) => {
    const controlsRef = useRef<OrbitControlsImpl | null>(null);
    const [loadError, setLoadError] = useState<string | null>(null);

    useImperativeHandle(ref, () => ({
      getCameraIntent: () => {
        const controls = controlsRef.current;
        if (!controls) return null;
        const camera = controls.object as THREE.PerspectiveCamera;
        return {
          position: [camera.position.x, camera.position.y, camera.position.z],
          target: [controls.target.x, controls.target.y, controls.target.z],
          fov: camera.fov,
        };
      },
    }), []);

    useEffect(() => setLoadError(null), [file]);

    return (
      <div className="flex flex-col gap-1">
        <div className="overflow-hidden rounded-lg border border-border-default">
          <Canvas
            camera={{ fov, position: [3, 2.3, -3], near: 0.01, far: 1000 }}
            style={{ height: 320, background: "#ffffff" }}
          >
            <ambientLight intensity={0.7} />
            <directionalLight position={[4, 6, 3]} intensity={1.2} />
            <directionalLight position={[-4, 2, -3]} intensity={0.4} />
            <PreviewScene file={file} fov={fov} controlsRef={controlsRef} onReady={() => onReady?.()} onError={setLoadError} />
            <OrbitControls ref={controlsRef} makeDefault maxPolarAngle={Math.PI / 2} />
          </Canvas>
        </div>
        {loadError ? (
          <p className="text-xs text-red-400">{loadError}</p>
        ) : (
          <p className="text-xs text-text-muted">Drag to orbit · scroll to zoom · the render matches this angle</p>
        )}
      </div>
    );
  },
);

StudioRenderPreview.displayName = "StudioRenderPreview";

export default StudioRenderPreview;
