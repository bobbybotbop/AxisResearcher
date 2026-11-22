import { useRef, useState } from "react";
import { useSyncExternalStore } from "react";
import {
  startPipeline,
  startTask,
  statusStore,
  type PipelineHandle,
  type TaskHandle,
} from "../utils/statusStore";

const DEMO_PIPELINE_STEPS = ["Fetch data", "Process items", "Upload results"];
const DEMO_STEP_TOTAL = 5;

/**
 * Temporary demo harness for the Status Store (ticket 01). Exercises the full
 * handle API from the Testing tab: a standalone task can be started,
 * progressed, succeeded, and failed; a pipeline can be started, advanced
 * step-by-step (with determinate progress), succeeded, and failed. Remove once
 * real features migrate onto the store.
 */
export default function StatusStoreDemo() {
  const { pipelines } = useSyncExternalStore(statusStore.subscribe, statusStore.getSnapshot);
  const taskHandle = useRef<TaskHandle | null>(null);
  const pipelineHandle = useRef<PipelineHandle | null>(null);
  const [taskStep, setTaskStep] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  const handleStartTask = () => {
    taskHandle.current = startTask("Demo task", { total: DEMO_STEP_TOTAL });
    setTaskStep(0);
  };

  const handleTaskProgress = () => {
    const next = taskStep + 1;
    setTaskStep(next);
    taskHandle.current?.progress(next);
  };

  const handleStartPipeline = () => {
    pipelineHandle.current = startPipeline("Demo pipeline", DEMO_PIPELINE_STEPS);
    setStepProgress(0);
  };

  const handlePipelineProgress = () => {
    const next = stepProgress + 1;
    setStepProgress(next);
    pipelineHandle.current?.progress(next, DEMO_STEP_TOTAL);
  };

  const handlePipelineAdvance = () => {
    pipelineHandle.current?.advance();
    setStepProgress(0);
  };

  const btn =
    "rounded-lg border border-border-default bg-surface-panel px-3 py-1.5 text-sm text-text-primary transition-colors hover:bg-surface-hover disabled:opacity-50";

  return (
    <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-4">
      <h3 className="text-lg font-semibold text-text-primary">
        Status Store demo (temporary)
      </h3>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-text-primary">Standalone task (toast, bottom-right)</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btn} onClick={handleStartTask}>
            Start task
          </button>
          <button type="button" className={btn} onClick={handleTaskProgress} disabled={!taskHandle.current}>
            Progress ({taskStep}/{DEMO_STEP_TOTAL})
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => taskHandle.current?.succeed("Demo task finished")}
            disabled={!taskHandle.current}
          >
            Succeed
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => taskHandle.current?.fail("Demo task failed")}
            disabled={!taskHandle.current}
          >
            Fail
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-text-primary">Pipeline (step tracker below)</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btn} onClick={handleStartPipeline}>
            Start pipeline
          </button>
          <button
            type="button"
            className={btn}
            onClick={handlePipelineProgress}
            disabled={!pipelineHandle.current}
          >
            Step progress ({stepProgress}/{DEMO_STEP_TOTAL})
          </button>
          <button
            type="button"
            className={btn}
            onClick={handlePipelineAdvance}
            disabled={!pipelineHandle.current}
          >
            Advance step
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => pipelineHandle.current?.succeed("Demo pipeline finished")}
            disabled={!pipelineHandle.current}
          >
            Succeed
          </button>
          <button
            type="button"
            className={btn}
            onClick={() => pipelineHandle.current?.fail("Demo pipeline failed")}
            disabled={!pipelineHandle.current}
          >
            Fail
          </button>
        </div>
      </div>

      {pipelines.length > 0 && (
        <div className="flex flex-col gap-3">
          {pipelines.map((p) => (
            <div key={p.id} className="rounded-lg border border-border-default bg-surface-muted p-3">
              <p className="mb-2 text-sm font-semibold text-text-primary">
                {p.name} — {p.status}
              </p>
              <ol className="flex flex-col gap-1">
                {p.steps.map((s, i) => (
                  <li key={s.id} className="flex items-center gap-2 text-sm">
                    <span aria-hidden="true">
                      {s.status === "success"
                        ? "✓"
                        : s.status === "error"
                          ? "✕"
                          : s.status === "running"
                            ? "◉"
                            : "○"}
                    </span>
                    <span
                      className={
                        s.status === "error"
                          ? "text-danger"
                          : i === p.currentIndex
                            ? "font-medium text-text-primary"
                            : "text-text-muted"
                      }
                    >
                      {s.name}
                    </span>
                    {s.progress && s.status === "running" && (
                      <span className="text-text-muted">
                        {s.progress.current} of {s.progress.total}
                      </span>
                    )}
                    {s.error && <span className="text-danger">— {s.error}</span>}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
