import { describe, expect, it } from "vitest";
import {
  UPLOAD_STEP_TITLES,
  applyUploadStreamEvent,
  failUploadStep,
  startUploadRun,
  succeedUploadRun,
} from "./uploadPipeline";

describe("startUploadRun", () => {
  it("begins with the prepare step running and upload pending", () => {
    const steps = startUploadRun();
    expect(steps.prepare.status).toBe("running");
    expect(steps.prepare.statusText).toBeTruthy();
    expect(steps.prepare.error).toBeUndefined();
    expect(steps.upload.status).toBe("pending");
  });

  it("resets a prior failed run so a retry starts clean", () => {
    const failed = failUploadStep(startUploadRun(), "boom");
    const retry = startUploadRun();
    expect(retry.prepare.status).toBe("running");
    expect(retry.prepare.error).toBeUndefined();
    expect(failed.prepare.error).toBe("boom");
  });
});

describe("applyUploadStreamEvent", () => {
  it("marks the prepare step success and upload running when prepare completes", () => {
    const steps = applyUploadStreamEvent(startUploadRun(), {
      step: "Preparing listing data",
      status: "completed",
    });
    expect(steps.prepare.status).toBe("success");
    expect(steps.upload.status).toBe("running");
  });

  it("marks a step running with a status line on in_progress", () => {
    const prepared = applyUploadStreamEvent(startUploadRun(), {
      step: "Preparing listing data",
      status: "completed",
    });
    const steps = applyUploadStreamEvent(prepared, {
      step: "Uploading to eBay",
      status: "in_progress",
    });
    expect(steps.prepare.status).toBe("success");
    expect(steps.upload.status).toBe("running");
    expect(steps.upload.statusText).toBeTruthy();
  });

  it("completes both steps when the upload step completes", () => {
    const steps = applyUploadStreamEvent(startUploadRun(), {
      step: "Uploading to eBay",
      status: "completed",
    });
    expect(steps.prepare.status).toBe("success");
    expect(steps.upload.status).toBe("success");
  });

  it("ignores unknown step names", () => {
    const before = startUploadRun();
    const after = applyUploadStreamEvent(before, {
      step: "Something else",
      status: "completed",
    });
    expect(after).toEqual(before);
  });
});

describe("succeedUploadRun", () => {
  it("marks every step success with the final status line", () => {
    const steps = succeedUploadRun(startUploadRun(), "Listing is now live on eBay");
    expect(steps.prepare.status).toBe("success");
    expect(steps.upload.status).toBe("success");
    expect(steps.upload.statusText).toBe("Listing is now live on eBay");
  });
});

describe("failUploadStep", () => {
  it("fails the running step with the error message", () => {
    const steps = failUploadStep(startUploadRun(), "eBay rejected the offer");
    expect(steps.prepare.status).toBe("error");
    expect(steps.prepare.error).toBe("eBay rejected the offer");
    expect(steps.upload.status).toBe("pending");
  });

  it("fails the first incomplete step when none is running", () => {
    const prepared = applyUploadStreamEvent(startUploadRun(), {
      step: "Preparing listing data",
      status: "completed",
    });
    const idle = { ...prepared, upload: { status: "pending" as const } };
    const steps = failUploadStep(idle, "connection lost");
    expect(steps.prepare.status).toBe("success");
    expect(steps.upload.status).toBe("error");
    expect(steps.upload.error).toBe("connection lost");
  });

  it("leaves a fully successful run untouched", () => {
    const done = succeedUploadRun(startUploadRun());
    expect(failUploadStep(done, "late error")).toEqual(done);
  });
});

describe("UPLOAD_STEP_TITLES", () => {
  it("titles both steps for the StepCard headers", () => {
    expect(UPLOAD_STEP_TITLES.prepare).toBe("Prepare listing data");
    expect(UPLOAD_STEP_TITLES.upload).toBe("Upload to eBay");
  });
});
