import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "./icons";
import { useOnboarding } from "./useOnboarding";

/**
 * First-run wizard that auto-appears for users whose onboarding isn't
 * complete. Mounted at the top of SuiteShell so every authenticated
 * route can get it. The panel is dismissable (Skip) — dismissal is
 * persisted server-side so it doesn't nag on the next login.
 *
 * Each step is intentionally lightweight: we either ask the user to
 * confirm something they can do right there (welcome / profile), or
 * we point them at an existing page (workspace / project / invite)
 * so the wizard isn't trying to duplicate settings UI.
 */
export default function OnboardingWizard() {
  const { status, completeStep, skip } = useOnboarding();
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  // Index of the first incomplete step — what the wizard opens on.
  const firstOpenIdx = useMemo(() => {
    if (!status) return 0;
    const done = new Set(status.completed);
    const idx = status.steps.findIndex((s) => !done.has(s.key));
    return idx < 0 ? status.steps.length - 1 : idx;
  }, [status]);

  if (!status || !status.show_wizard) return null;

  const current = activeIdx ?? firstOpenIdx;
  const step = status.steps[current];
  const done = new Set(status.completed);

  const advance = async () => {
    await completeStep(step.key);
    // Re-read the current index from fresh status next render.
    if (current < status.steps.length - 1) setActiveIdx(current + 1);
  };

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
      <div className="onboarding-card">
        <header className="onboarding-head">
          <div>
            <div className="onboarding-eyebrow">Getting started</div>
            <h2 id="onboarding-title" className="onboarding-title">Welcome to PM Project</h2>
          </div>
          <button className="btn btn-sm" onClick={skip} aria-label="Skip setup">
            Skip for now
          </button>
        </header>

        <div className="onboarding-body">
          <ol className="onboarding-steps" aria-label="Setup checklist">
            {status.steps.map((s, i) => {
              const completed = done.has(s.key);
              const active = i === current;
              return (
                <li
                  key={s.key}
                  className={`onboarding-step ${active ? "active" : ""} ${completed ? "done" : ""}`}
                >
                  <button
                    type="button"
                    className="onboarding-step-btn"
                    onClick={() => setActiveIdx(i)}
                    aria-current={active ? "step" : undefined}
                  >
                    <span className="onboarding-step-num" aria-hidden>
                      {completed ? <Icon.Check size={12} /> : i + 1}
                    </span>
                    <span className="onboarding-step-label">{s.title}</span>
                  </button>
                </li>
              );
            })}
          </ol>

          <div className="onboarding-pane">
            <h3 className="onboarding-pane-title">{step.title}</h3>
            <p className="onboarding-pane-description">{step.description}</p>

            <StepContent stepKey={step.key} />

            <div className="onboarding-actions">
              {current > 0 && (
                <button className="btn" onClick={() => setActiveIdx(current - 1)}>
                  Back
                </button>
              )}
              <button className="btn btn-primary" onClick={advance}>
                {current === status.steps.length - 1 ? "Finish" : "Mark done & continue"}
              </button>
            </div>
          </div>
        </div>

        <footer className="onboarding-foot">
          <span>{done.size} of {status.steps.length} complete</span>
          <div className="onboarding-progress">
            <div
              className="onboarding-progress-bar"
              style={{ width: `${(done.size / status.steps.length) * 100}%` }}
            />
          </div>
        </footer>
      </div>
    </div>
  );
}


/** Per-step body: either inline action shortcuts or a link to the relevant
 * page. The backend auto-detects workspace/project completion when the user
 * gets to them via these links, so we don't need to POST a step explicitly. */
function StepContent({ stepKey }: { stepKey: string }) {
  switch (stepKey) {
    case "welcome":
      return (
        <p className="onboarding-copy">
          This quick setup takes about a minute. You can skip any step and come
          back to it from Settings → Getting started.
        </p>
      );
    case "profile":
      return (
        <div className="onboarding-copy">
          <p>Make sure your name and timezone are right so teammates see your activity in their local time.</p>
          <Link to="/settings" className="btn btn-sm">
            Open profile settings
          </Link>
        </div>
      );
    case "workspace":
      return (
        <div className="onboarding-copy">
          <p>Workspaces keep each company or client isolated. You can be a member of more than one.</p>
          <Link to="/admin/workspaces" className="btn btn-sm">
            Manage workspaces
          </Link>
        </div>
      );
    case "first_project":
      return (
        <div className="onboarding-copy">
          <p>Projects are where tasks, deliverables, and files live. Try creating one now.</p>
          <Link to="/projects" className="btn btn-sm">
            Go to projects
          </Link>
        </div>
      );
    case "invite":
      return (
        <div className="onboarding-copy">
          <p>Invite teammates so they can see what you're working on. You can do this any time.</p>
          <Link to="/admin/users" className="btn btn-sm">
            Invite teammates
          </Link>
        </div>
      );
    default:
      return null;
  }
}
