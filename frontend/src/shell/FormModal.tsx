import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { Icon } from "./icons";

export type FormModalFieldKind = "text" | "textarea" | "number" | "email" | "select" | "date" | "checkbox";

export type FormModalField = {
  name: string;
  label: string;
  kind?: FormModalFieldKind;
  placeholder?: string;
  required?: boolean;
  defaultValue?: string | number | boolean;
  options?: { value: string; label: string }[];
  helperText?: string;
  min?: number;
  max?: number;
  step?: number;
  rows?: number;
};

export type FormModalValues = Record<string, string>;

export type FormModalProps = {
  open: boolean;
  title: string;
  description?: string;
  fields?: FormModalField[];
  submitLabel?: string;
  cancelLabel?: string;
  dangerous?: boolean;
  body?: ReactNode;
  onSubmit: (values: FormModalValues) => void | Promise<void>;
  onCancel: () => void;
};

export default function FormModal({
  open,
  title,
  description,
  fields = [],
  submitLabel = "Save",
  cancelLabel = "Cancel",
  dangerous = false,
  body,
  onSubmit,
  onCancel,
}: FormModalProps) {
  const initialValues = useMemo(() => {
    const out: FormModalValues = {};
    for (const f of fields) {
      if (f.defaultValue !== undefined) out[f.name] = String(f.defaultValue);
      else if (f.kind === "checkbox") out[f.name] = "";
      else out[f.name] = "";
    }
    return out;
  }, [fields]);
  const [values, setValues] = useState<FormModalValues>(initialValues);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null>(null);

  useEffect(() => {
    if (open) {
      setValues(initialValues);
      setError(null);
      setSubmitting(false);
    }
  }, [open, initialValues]);

  useEffect(() => {
    if (!open) return;
    const prevActive = document.activeElement as HTMLElement | null;
    const timeout = window.setTimeout(() => {
      firstFieldRef.current?.focus();
    }, 30);
    return () => {
      window.clearTimeout(timeout);
      prevActive?.focus?.();
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCancel();
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const focusables = panelRef.current.querySelectorAll<HTMLElement>(
          'input, select, textarea, button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      for (const f of fields) {
        if (f.required && f.kind !== "checkbox" && !(values[f.name] ?? "").trim()) {
          setError(`${f.label} is required`);
          return;
        }
      }
      setSubmitting(true);
      setError(null);
      try {
        await onSubmit({ ...values });
      } catch (err: any) {
        setError(err?.data?.detail || err?.message || "Something went wrong");
      } finally {
        setSubmitting(false);
      }
    },
    [fields, values, onSubmit],
  );

  if (!open) return null;

  const node = (
    <div
      className="form-modal-root"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="form-modal-panel" ref={panelRef}>
        <form onSubmit={handleSubmit}>
          <header className="form-modal-head">
            <h2 id={titleId} className="form-modal-title">{title}</h2>
            <button
              type="button"
              className="form-modal-close"
              onClick={onCancel}
              aria-label="Close"
            >
              <Icon.Close size={16} />
            </button>
          </header>
          {description && <p className="form-modal-desc">{description}</p>}
          <div className="form-modal-body">
            {body}
            {fields.map((f, i) => (
              <FieldInput
                key={f.name}
                field={f}
                value={values[f.name] ?? ""}
                onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))}
                inputRef={i === 0 ? (firstFieldRef as any) : undefined}
              />
            ))}
            {error && <div className="form-modal-error" role="alert">{error}</div>}
          </div>
          <footer className="form-modal-foot">
            <button type="button" className="btn btn-sm" onClick={onCancel} disabled={submitting}>
              {cancelLabel}
            </button>
            <button
              type="submit"
              className={`btn btn-sm ${dangerous ? "btn-danger" : "btn-primary"}`}
              disabled={submitting}
            >
              {submitting ? "Working…" : submitLabel}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
  return createPortal(node, document.body);
}

function FieldInput({
  field,
  value,
  onChange,
  inputRef,
}: {
  field: FormModalField;
  value: string;
  onChange: (v: string) => void;
  inputRef?: React.Ref<any>;
}) {
  const id = useId();
  const common = {
    id,
    name: field.name,
    placeholder: field.placeholder,
    required: field.required,
  };
  return (
    <div className="form-group">
      <label htmlFor={id}>
        {field.label}
        {field.required && <span className="form-modal-required" aria-hidden> *</span>}
      </label>
      {field.kind === "textarea" ? (
        <textarea
          {...common}
          ref={inputRef as any}
          rows={field.rows ?? 3}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : field.kind === "select" ? (
        <select
          {...common}
          ref={inputRef as any}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">{field.placeholder ?? "Select…"}</option>
          {(field.options ?? []).map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ) : field.kind === "checkbox" ? (
        <label className="form-modal-check">
          <input
            type="checkbox"
            ref={inputRef as any}
            checked={value === "true"}
            onChange={(e) => onChange(e.target.checked ? "true" : "")}
          />
          <span>{field.placeholder ?? field.label}</span>
        </label>
      ) : (
        <input
          {...common}
          ref={inputRef as any}
          type={field.kind === "number" ? "number" : field.kind === "email" ? "email" : field.kind === "date" ? "date" : "text"}
          value={value}
          min={field.min}
          max={field.max}
          step={field.step}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {field.helperText && <div className="form-modal-helper">{field.helperText}</div>}
    </div>
  );
}
