import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";
import {
  DEFAULT_VIEW_DIRECTION,
  modelExtensionOf,
  PREVIEW_FRAME_MARGIN,
  PREVIEW_INITIAL_CAMERA,
  PREVIEW_MATERIAL_DEFAULTS,
  rigCameraDirection,
  type RenderRigCamera,
} from "../constants/render";

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

const defaultViewDirection = new THREE.Vector3(...DEFAULT_VIEW_DIRECTION).normalize();

// Build the preview object so it matches what Blender shows for the same file:
// STL/PLY are imported raw (Z-up) by Blender, so rotate them upright in the
// Y-up preview; Blender's OBJ importer converts Y-up -> Z-up itself, and
// three.js loads OBJ raw, so OBJ needs no rotation.
const loadModel = async (file: File): Promise<THREE.Object3D> => {
  const material = new THREE.MeshStandardMaterial(PREVIEW_MATERIAL_DEFAULTS);
  const ext = modelExtensionOf(file.name);
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

// Where the camera ends up for a given rig angle: auto-framed like the render
// (bounding sphere + FOV + margin), direction from the backend's az/el math.
const rigCameraPosition = (
  camera: RenderRigCamera,
  center: THREE.Vector3,
  radius: number,
  fov: number,
): THREE.Vector3 => {
  const distance = (radius / Math.tan(THREE.MathUtils.degToRad(fov) / 2)) * PREVIEW_FRAME_MARGIN;
  const direction = new THREE.Vector3(...rigCameraDirection(camera.azimuth, camera.elevation));
  return center.clone().addScaledVector(direction, distance);
};

interface PreviewSceneProps {
  file: File;
  fov: number;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onReady: () => void;
  onError: (message: string) => void;
  // Rig Overview: wireframe frustums + sight lines for every rig camera
  rig?: RenderRigCamera[];
  selectedCamera?: number;
  // POV thumbnail mode: lock the camera at this rig angle (no orbit controls)
  fixedCamera?: RenderRigCamera;
}

function PreviewScene({ file, fov, controlsRef, onReady, onError, rig, selectedCamera, fixedCamera }: PreviewSceneProps) {
  const camera = useThree((s) => s.camera);
  const [model, setModel] = useState<THREE.Object3D | null>(null);
  const [frame, setFrame] = useState<{ center: THREE.Vector3; radius: number } | null>(null);
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
        setFrame({ center: sphere.center.clone(), radius: sphere.radius });
        const distance = (sphere.radius / Math.tan(THREE.MathUtils.degToRad(fov) / 2)) * PREVIEW_FRAME_MARGIN;
        if (camera instanceof THREE.PerspectiveCamera) {
          const startDirection = fixedCamera
            ? new THREE.Vector3(...rigCameraDirection(fixedCamera.azimuth, fixedCamera.elevation))
            : defaultViewDirection;
          camera.position.copy(sphere.center).addScaledVector(startDirection, distance);
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
      setFrame(null);
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

  // POV thumbnail mode: re-frame whenever the fixed rig camera changes
  useEffect(() => {
    if (!fixedCamera || !frame || !(camera instanceof THREE.PerspectiveCamera)) return;
    camera.position.copy(rigCameraPosition(fixedCamera, frame.center, frame.radius, fov));
    camera.fov = fov;
    camera.updateProjectionMatrix();
    camera.lookAt(frame.center);
  }, [fixedCamera, frame, fov, camera]);

  if (!model) return null;
  return (
    <>
      <primitive object={model} />
      {rig && frame && (
        <RigOverviewHelpers rig={rig} center={frame.center} radius={frame.radius} fov={fov} selectedCamera={selectedCamera} />
      )}
    </>
  );
}

// Rig Overview helpers: one wireframe frustum + a sight line per rig camera.
// The frustum is a THREE.CameraHelper on a throwaway PerspectiveCamera placed
// at the auto-framed rig position; the sight line runs from the camera to the
// model center. The selected camera is highlighted in the primary color.
function RigOverviewHelpers({
  rig,
  center,
  radius,
  fov,
  selectedCamera,
}: {
  rig: RenderRigCamera[];
  center: THREE.Vector3;
  radius: number;
  fov: number;
  selectedCamera?: number;
}) {
  const helpers = useMemo(() => {
    const group = new THREE.Group();
    rig.forEach((rigCamera, index) => {
      const position = rigCameraPosition(rigCamera, center, radius, fov);
      const frustumCamera = new THREE.PerspectiveCamera(fov, 1, radius * 0.05, radius * 1.2);
      frustumCamera.position.copy(position);
      frustumCamera.lookAt(center);
      frustumCamera.updateProjectionMatrix();
      frustumCamera.updateMatrixWorld(true);
      const selected = index === selectedCamera;
      const helper = new THREE.CameraHelper(frustumCamera);
      const material = helper.material as THREE.LineBasicMaterial;
      material.color = new THREE.Color(selected ? "#3b82f6" : "#94a3b8");
      material.depthTest = false;
      helper.renderOrder = 999;
      group.add(helper);

      const lineGeometry = new THREE.BufferGeometry().setFromPoints([position, center]);
      const line = new THREE.Line(
        lineGeometry,
        new THREE.LineBasicMaterial({ color: selected ? "#3b82f6" : "#cbd5e1", depthTest: false }),
      );
      line.renderOrder = 999;
      group.add(line);
    });
    return group;
  }, [rig, center, radius, fov, selectedCamera]);

  useEffect(() => () => {
    helpers.traverse((child) => {
      if (child instanceof THREE.CameraHelper) child.dispose();
      if (child instanceof THREE.Line) {
        child.geometry.dispose();
        (child.material as THREE.Material).dispose();
      }
    });
  }, [helpers]);

  return <primitive object={helpers} />;
}

interface StudioRenderPreviewProps {
  file: File;
  fov: number;
  onReady?: () => void;
  // Square viewer (Profile Editor): the canvas fills an aspect-square container
  // instead of the fixed 320px height used in Step 4
  square?: boolean;
  // Rig Overview (Multi Shot Mode): wireframe frustums + sight lines
  rig?: RenderRigCamera[];
  selectedCamera?: number;
  // POV thumbnail mode: fixed camera at this rig angle, no orbit controls
  fixedCamera?: RenderRigCamera;
  // Hide the hint line under the canvas (POV thumbnails are self-explanatory)
  hideHint?: boolean;
}

const StudioRenderPreview = forwardRef<StudioRenderPreviewHandle, StudioRenderPreviewProps>(
  ({ file, fov, onReady, square = false, rig, selectedCamera, fixedCamera, hideHint = false }, ref) => {
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
        <div className={`overflow-hidden rounded-lg border border-border-default ${square ? "aspect-square w-full" : ""}`}>
          <Canvas
            camera={{ fov, ...PREVIEW_INITIAL_CAMERA }}
            style={square ? { width: "100%", height: "100%", background: "#ffffff" } : { height: 320, background: "#ffffff" }}
          >
            <ambientLight intensity={0.7} />
            <directionalLight position={[4, 6, 3]} intensity={1.2} />
            <directionalLight position={[-4, 2, -3]} intensity={0.4} />
            <PreviewScene
              file={file}
              fov={fov}
              controlsRef={controlsRef}
              onReady={() => onReady?.()}
              onError={setLoadError}
              rig={rig}
              selectedCamera={selectedCamera}
              fixedCamera={fixedCamera}
            />
            {!fixedCamera && <OrbitControls ref={controlsRef} makeDefault />}
          </Canvas>
        </div>
        {loadError ? (
          <p className="text-xs text-red-400">{loadError}</p>
        ) : hideHint ? null : (
          <p className="text-xs text-text-muted">Drag to orbit to choose the render angle · field of view is adjusted below</p>
        )}
      </div>
    );
  },
);

StudioRenderPreview.displayName = "StudioRenderPreview";

export default StudioRenderPreview;
