import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import FormModal from "./FormModal";
import type { FormModalField, FormModalValues } from "./FormModal";

type PromptSpec = {
  kind: "prompt";
  title: string;
  description?: string;
  fields: FormModalField[];
  submitLabel?: string;
  cancelLabel?: string;
  resolve: (v: FormModalValues | null) => void;
};

type ConfirmSpec = {
  kind: "confirm";
  title: string;
  description?: string;
  body?: ReactNode;
  submitLabel?: string;
  cancelLabel?: string;
  dangerous?: boolean;
  resolve: (v: boolean) => void;
};

type AlertSpec = {
  kind: "alert";
  title: string;
  description?: string;
  resolve: () => void;
};

type AnySpec = PromptSpec | ConfirmSpec | AlertSpec;

type Listener = (spec: AnySpec | null) => void;
let listener: Listener | null = null;
let pending: AnySpec | null = null;

function push(spec: AnySpec) {
  pending = spec;
  listener?.(spec);
}

function clear() {
  pending = null;
  listener?.(null);
}

export function promptForValues(opts: {
  title: string;
  description?: string;
  fields: FormModalField[];
  submitLabel?: string;
  cancelLabel?: string;
}): Promise<FormModalValues | null> {
  return new Promise((resolve) => {
    push({ kind: "prompt", ...opts, resolve });
  });
}

export function confirmAction(opts: {
  title: string;
  description?: string;
  body?: ReactNode;
  submitLabel?: string;
  cancelLabel?: string;
  dangerous?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    push({ kind: "confirm", ...opts, resolve });
  });
}

export function notifyUser(opts: { title: string; description?: string }): Promise<void> {
  return new Promise((resolve) => {
    push({ kind: "alert", ...opts, resolve });
  });
}

export default function ModalHost() {
  const [spec, setSpec] = useState<AnySpec | null>(pending);

  useEffect(() => {
    listener = setSpec;
    return () => {
      if (listener === setSpec) listener = null;
    };
  }, []);

  if (!spec) return null;

  if (spec.kind === "prompt") {
    return (
      <FormModal
        open
        title={spec.title}
        description={spec.description}
        fields={spec.fields}
        submitLabel={spec.submitLabel ?? "Save"}
        cancelLabel={spec.cancelLabel ?? "Cancel"}
        onSubmit={(values) => {
          spec.resolve(values);
          clear();
        }}
        onCancel={() => {
          spec.resolve(null);
          clear();
        }}
      />
    );
  }

  if (spec.kind === "confirm") {
    return (
      <FormModal
        open
        title={spec.title}
        description={spec.description}
        body={spec.body}
        fields={[]}
        submitLabel={spec.submitLabel ?? "Confirm"}
        cancelLabel={spec.cancelLabel ?? "Cancel"}
        dangerous={spec.dangerous}
        onSubmit={() => {
          spec.resolve(true);
          clear();
        }}
        onCancel={() => {
          spec.resolve(false);
          clear();
        }}
      />
    );
  }

  return (
    <FormModal
      open
      title={spec.title}
      description={spec.description}
      fields={[]}
      submitLabel="OK"
      cancelLabel="Close"
      onSubmit={() => {
        spec.resolve();
        clear();
      }}
      onCancel={() => {
        spec.resolve();
        clear();
      }}
    />
  );
}
