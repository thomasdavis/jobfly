import { useRef, useState } from "react";
import { FileJson, Upload, X } from "lucide-react";
import { api } from "../api";

export default function ImportDialog({
  onClose,
  onLoaded,
  llm,
}: {
  onClose: () => void;
  onLoaded: () => void;
  llm: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null),
    file = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"resume" | "jobs">("resume"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function load(file: File) {
    setBusy(true);
    setError("");
    try {
      if (file.size > 2_000_000)
        throw new Error("Choose a JSON file smaller than 2 MB.");
      const data = JSON.parse(await file.text());
      await api(
        mode === "resume" ? "resume" : "import",
        mode === "resume"
          ? { resume: data }
          : { jobs: Array.isArray(data) ? data : data.jobs },
      );
      onLoaded();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={(el) => {
        dialog.current = el;
        if (el && !el.open) el.showModal();
      }}
      className="import-dialog"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <div className="dialog-head">
        <FileJson size={24} />
        <button
          className="icon-button"
          aria-label="Close import"
          disabled={busy}
          onClick={onClose}
        >
          <X size={19} />
        </button>
      </div>
      <h2>Make this habitat yours.</h2>
      <p>
        Bring your resume. We’ll turn your matches into a world worth exploring.
      </p>
      <div className="import-tabs">
        <button
          aria-pressed={mode === "resume"}
          onClick={() => setMode("resume")}
          disabled={busy}
        >
          JSON Resume
        </button>
        <button
          aria-pressed={mode === "jobs"}
          onClick={() => setMode("jobs")}
          disabled={busy}
        >
          Saved jobs
        </button>
      </div>
      <button
        className="upload-zone"
        disabled={busy}
        onClick={() => file.current?.click()}
      >
        <Upload size={26} />
        <strong>
          {busy
            ? "Preparing your habitat…"
            : `Choose ${mode === "resume" ? "resume" : "jobs"}.json`}
        </strong>
        <span>
          {mode === "resume"
            ? "A standard JSON Resume file"
            : "An array of jobs or { jobs: [...] }"}
        </span>
      </button>
      <input
        className="sr-only"
        ref={file}
        type="file"
        accept=".json,application/json"
        onChange={(e) => {
          if (e.target.files?.[0]) void load(e.target.files[0]);
          e.target.value = "";
        }}
      />
      <p className="data-note">
        {mode === "resume"
          ? "Your resume is sent to JSON Resume’s matching API. Matches and feedback are saved on this machine."
          : "Each job needs a title and company. Imported jobs stay on this machine."}
      </p>
      {llm && (
        <p className="data-note">
          An optional LLM interpreter is configured. You can run it from the
          notebook after import.
        </p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </dialog>
  );
}
