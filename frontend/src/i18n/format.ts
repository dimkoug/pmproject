import { useAppSelector } from "../app/hooks";

/** Resolved user locale + timezone. Falls back to browser defaults if unset. */
export function useUserLocale() {
  const user = useAppSelector((s) => s.auth.user);
  return {
    language: (user?.language as string | undefined) || (typeof navigator !== "undefined" ? navigator.language : "en"),
    timezone: (user?.timezone as string | undefined) || (Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"),
  };
}

const dtfCache = new Map<string, Intl.DateTimeFormat>();
const nfCache = new Map<string, Intl.NumberFormat>();

function dtf(locale: string, tz: string, opts: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = `${locale}|${tz}|${JSON.stringify(opts)}`;
  let f = dtfCache.get(key);
  if (!f) {
    f = new Intl.DateTimeFormat(locale, { ...opts, timeZone: tz });
    dtfCache.set(key, f);
  }
  return f;
}

function nf(locale: string, opts: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = `${locale}|${JSON.stringify(opts)}`;
  let f = nfCache.get(key);
  if (!f) {
    f = new Intl.NumberFormat(locale, opts);
    nfCache.set(key, f);
  }
  return f;
}

function toDate(input: string | number | Date | null | undefined): Date | null {
  if (input === null || input === undefined || input === "") return null;
  const d = input instanceof Date ? input : new Date(input);
  return isNaN(d.getTime()) ? null : d;
}

/** React hook — returns formatters bound to the current user's locale + timezone. */
export function useFormat() {
  const { language, timezone } = useUserLocale();

  const formatDate = (
    input: string | number | Date | null | undefined,
    options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "2-digit" },
  ): string => {
    const d = toDate(input);
    if (!d) return "—";
    return dtf(language, timezone, options).format(d);
  };

  const formatDateTime = (
    input: string | number | Date | null | undefined,
    options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" },
  ): string => {
    const d = toDate(input);
    if (!d) return "—";
    return dtf(language, timezone, options).format(d);
  };

  const formatTime = (input: string | number | Date | null | undefined): string => {
    const d = toDate(input);
    if (!d) return "—";
    return dtf(language, timezone, { hour: "2-digit", minute: "2-digit" }).format(d);
  };

  const formatRelative = (input: string | number | Date | null | undefined): string => {
    const d = toDate(input);
    if (!d) return "—";
    const diffMs = d.getTime() - Date.now();
    const diffSec = Math.round(diffMs / 1000);
    const abs = Math.abs(diffSec);
    const rtf = new Intl.RelativeTimeFormat(language, { numeric: "auto" });
    if (abs < 60) return rtf.format(diffSec, "second");
    if (abs < 3600) return rtf.format(Math.round(diffSec / 60), "minute");
    if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), "hour");
    if (abs < 2592000) return rtf.format(Math.round(diffSec / 86400), "day");
    if (abs < 31536000) return rtf.format(Math.round(diffSec / 2592000), "month");
    return rtf.format(Math.round(diffSec / 31536000), "year");
  };

  const formatCurrency = (
    amount: number | null | undefined,
    currency: string = "USD",
  ): string => {
    if (amount === null || amount === undefined) return "—";
    return nf(language, { style: "currency", currency, maximumFractionDigits: 2 }).format(amount);
  };

  const formatNumber = (
    n: number | null | undefined,
    options: Intl.NumberFormatOptions = {},
  ): string => {
    if (n === null || n === undefined) return "—";
    return nf(language, options).format(n);
  };

  const formatPercent = (n: number | null | undefined, fractionDigits: number = 1): string => {
    if (n === null || n === undefined) return "—";
    return nf(language, { style: "percent", minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits }).format(n);
  };

  return { formatDate, formatDateTime, formatTime, formatRelative, formatCurrency, formatNumber, formatPercent, language, timezone };
}

/** Standalone helpers for contexts where hooks aren't available (e.g. imperative logic).
 *  Pass locale + timezone explicitly. */
export function formatDateIn(
  input: string | number | Date | null | undefined,
  locale: string,
  timezone: string,
  options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" },
): string {
  const d = toDate(input);
  if (!d) return "—";
  return dtf(locale, timezone, options).format(d);
}

/** Common IANA zones exposed as a picklist. Not exhaustive — user can type for custom. */
export const COMMON_TIMEZONES = [
  "UTC",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Athens",
  "Europe/Madrid",
  "Europe/Amsterdam",
  "Europe/Moscow",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Sao_Paulo",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Asia/Singapore",
  "Asia/Jerusalem",
  "Africa/Cairo",
  "Africa/Johannesburg",
  "Australia/Sydney",
  "Pacific/Auckland",
];
