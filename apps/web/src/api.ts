import type { components } from "./api.generated";
export type Schema = components["schemas"];
export type Snapshot = Schema["MoneySnapshot"];
export type SnapshotView = Schema["SnapshotView"];
export type Calculation = Schema["Calculation"];
export type Plan = Schema["PlanView"];
export type Transaction = Schema["TransactionView"];
export type Job = Schema["JobView"];
export type Auth = Schema["AuthView"];

let csrf = "";
export const setCsrf = (value: string) => {
  csrf = value;
};
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data: { detail?: unknown };
  try {
    data = await response.json();
  } catch {
    throw new Error("Сервер не відповів. Спробуйте ще раз.");
  }
  if (!response.ok) {
    if (response.status === 401 && !path.includes("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : response.status === 422
          ? "Перевірте поля: суми в євро, обов’язкові дати й назви."
          : "Не вдалося виконати дію.";
    throw new Error(
      response.status === 409 ? "Дію не виконано: " + detail : detail,
    );
  }
  return data as T;
}

export const money = (minor: number | null | undefined) => {
  if (minor == null || !Number.isSafeInteger(minor)) return "—";
  const value = BigInt(minor);
  const whole = value / 100n;
  const fraction = (value < 0n ? -value : value) % 100n;
  return new Intl.NumberFormat("uk-UA", { style: "currency", currency: "EUR" })
    .formatToParts(minor < 0 && whole === 0n ? -0 : whole)
    .map((part) =>
      part.type === "fraction"
        ? fraction.toString().padStart(2, "0")
        : part.value,
    )
    .join("");
};
export const euros = (minor: number | null | undefined) => {
  if (minor == null || !Number.isSafeInteger(minor)) return "";
  const value = BigInt(minor);
  const absolute = value < 0n ? -value : value;
  return `${minor < 0 ? "-" : ""}${absolute / 100n}.${(absolute % 100n).toString().padStart(2, "0")}`;
};
export function cents(value: string): number {
  const clean = value.trim().replace(",", ".");
  if (!/^-?\d+(\.\d{1,2})?$/.test(clean))
    throw new Error("Введіть суму з максимум двома цифрами після коми.");
  const negative = clean.startsWith("-");
  const [whole, fraction = ""] = clean.replace("-", "").split(".");
  const result = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
  if (result > BigInt(Number.MAX_SAFE_INTEGER))
    throw new Error("Сума завелика.");
  return Number(negative ? -result : result);
}
export const today = () => new Date().toISOString().slice(0, 10);
