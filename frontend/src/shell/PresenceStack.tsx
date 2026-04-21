import { usePresence } from "./usePresence";
import { useAppSelector } from "../app/hooks";

type Props = {
  entityType: string;
  entityId: string | null | undefined;
  /** Max avatars to render before showing a "+N" pill. */
  max?: number;
};

/** A compact avatar stack showing other users currently viewing this entity. */
export default function PresenceStack({ entityType, entityId, max = 4 }: Props) {
  const me = useAppSelector((s) => s.auth.user);
  const viewers = usePresence(entityType, entityId ?? null).filter(v => v.user_id !== me?.id);
  if (viewers.length === 0) return null;

  const shown = viewers.slice(0, max);
  const extra = viewers.length - shown.length;

  return (
    <div className="presence-stack" title={`${viewers.length} other ${viewers.length === 1 ? "person" : "people"} viewing`}>
      {shown.map((v) => (
        <span key={v.user_id} className="presence-avatar" title={v.name || v.email}>
          {initials(v.name || v.email)}
        </span>
      ))}
      {extra > 0 && <span className="presence-avatar presence-avatar-more">+{extra}</span>}
    </div>
  );
}

function initials(s: string) {
  return s
    .split(/\s+|[.@]/)
    .filter(Boolean)
    .map((p) => p[0]!.toUpperCase())
    .slice(0, 2)
    .join("");
}
