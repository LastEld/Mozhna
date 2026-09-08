import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  api,
  cents,
  euros,
  money,
  setCsrf,
  today,
  type Auth,
  type Calculation,
  type Job,
  type Plan,
  type Schema,
  type Snapshot,
  type SnapshotView,
  type Transaction,
} from "./api";

type Page = "now" | "plans" | "movement" | "earn" | "settings";
type ProviderState = Schema["ProviderStateView"];
type Schedule = Schema["ScheduleView"];
const titles: Record<Page, string> = {
  now: "Зараз",
  plans: "Мої плани",
  movement: "Рух коштів",
  earn: "Можливості доходу",
  settings: "Мій простір",
};
const states: Record<string, string> = {
  proposed: "Пропозиція",
  active: "Активний",
  rejected: "Не підходить",
  completed: "Завершений",
  queued: "У черзі",
  running: "Виконується",
  succeeded: "Готово",
  failed: "Не виконано",
  canceled: "Скасовано",
  waiting_provider: "Очікує модель",
};
const decisionNames = {
  CAN: "Можна",
  CAN_WITH_TRADEOFF: "Можна, але…",
  CANNOT: "Ще ні",
  UNKNOWN: "Потрібні дані",
};
const decisionText = {
  CAN: "Обов’язкові витрати, резерв і ціль залишаються покритими в межах розрахунку.",
  CAN_WITH_TRADEOFF:
    "Обов’язкові витрати й резерв покриті, але коштів на заплановану ціль стане менше.",
  CANNOT: "Покупка перетинає резерв або залишає непокриті зобов’язання.",
  UNKNOWN:
    "Оновіть залишок і перевірте повноту даних. Зараз надійної відповіді немає.",
};
function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    now: "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
    plans: "M5 5h14v16H5zM9 3h6v4H9zM8 12h8M8 16h5",
    movement: "M3 7h16l-4-4M21 17H5l4 4",
    earn: "M8 7V4h8v3M3 7h18v14H3zM3 12h18M10 12v3h4v-3",
    settings:
      "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4",
    plus: "M12 5v14M5 12h14",
    arrow: "M5 12h14M14 7l5 5-5 5",
    close: "M6 6l12 12M18 6 6 18",
    logout: "M10 4H4v16h6M14 8l4 4-4 4M8 12h10",
    check: "M5 12l4 4L19 6",
    refresh: "M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M18 18A8 8 0 0 1 5 15",
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.now} />
    </svg>
  );
}
function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [operationError, setOperationError] = useState("");
  useEffect(() => {
    const listener = (event: Event) =>
      setOperationError((event as CustomEvent<string>).detail);
    window.addEventListener("operation-error", listener);
    return () => window.removeEventListener("operation-error", listener);
  }, []);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Закрити" onClick={onClose}>
          <Icon name="close" />
        </button>
      </div>
      {operationError && (
        <p className="error-text" role="alert">
          {operationError}
        </p>
      )}
      {children}
    </dialog>
  );
}
function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-mark">
        <Icon name="plans" size={28} />
      </span>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<Auth | null>(null),
    [ready, setReady] = useState(false),
    [page, setPage] = useState<Page>("now");
  const [snapshot, setSnapshot] = useState<SnapshotView>({
    version: 0,
    snapshot: null,
    calculation: null,
  });
  const [plans, setPlans] = useState<Plan[]>([]),
    [transactions, setTransactions] = useState<Transaction[]>([]),
    [jobs, setJobs] = useState<Job[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [providers, setProviders] = useState<ProviderState>({
    items: [],
    metered_inference_enabled: false,
    daily_job_limit: 0,
    limitations: [],
  });
  const [modal, setModal] = useState<
    "snapshot" | "spend" | "plan" | "transaction" | "import" | "delete" | null
  >(null);
  const [observation, setObservation] = useState<Plan | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const fail = (e: unknown) => {
    const message = e instanceof Error ? e.message : "Дію не вдалося виконати.";
    setError(message);
    window.dispatchEvent(
      new CustomEvent("operation-error", { detail: message }),
    );
  };
  const loadGeneration = useRef(0);
  const mutationInFlight = useRef(false);
  async function load() {
    const generation = ++loadGeneration.current;
    const [s, p, t, j, pr, sc] = await Promise.all([
      api<SnapshotView>("/snapshot"),
      api<{ items: Plan[] }>("/plans"),
      api<{ items: Transaction[] }>("/transactions"),
      api<{ items: Job[] }>("/jobs"),
      api<ProviderState>("/providers"),
      api<{ items: Schedule[] }>("/schedules"),
    ]);
    if (generation !== loadGeneration.current) return;
    setSnapshot(s);
    setPlans(p.items);
    setTransactions(t.items);
    setJobs(j.items);
    setProviders(pr);
    setSchedules(sc.items);
  }
  useEffect(() => {
    api<Auth>("/auth/me")
      .then((u) => {
        setCsrf(u.csrf_token);
        setUser(u);
      })
      .catch(() => {})
      .finally(() => setReady(true));
    const expire = () => {
      loadGeneration.current += 1;
      setModal(null);
      setObservation(null);
      setSchedules([]);
      setUser(null);
      setSnapshot({ version: 0, snapshot: null, calculation: null });
      setPlans([]);
      setTransactions([]);
      setJobs([]);
      setCsrf("");
    };
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener("session-expired", expire);
    window.addEventListener("online", connection);
    window.addEventListener("offline", connection);
    return () => {
      window.removeEventListener("session-expired", expire);
      window.removeEventListener("online", connection);
      window.removeEventListener("offline", connection);
    };
  }, []);
  useEffect(() => {
    if (!user) return;
    load().catch(fail);
    const timer = setInterval(() => {
      const generation = loadGeneration.current;
      if (navigator.onLine)
        api<{ items: Job[] }>("/jobs")
          .then((r) => {
            if (generation === loadGeneration.current) setJobs(r.items);
          })
          .catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, [user]);
  useEffect(() => {
    if (!user) return;
    const refresh = () => {
      if (navigator.onLine) load().catch(fail);
    };
    const timer = setInterval(refresh, 60000);
    window.addEventListener("focus", refresh);
    window.addEventListener("online", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("online", refresh);
    };
  }, [user]);
  useEffect(() => {
    if (notice) {
      const t = setTimeout(() => setNotice(""), 5000);
      return () => clearTimeout(t);
    }
  }, [notice]);
  async function action(work: () => Promise<unknown>, message = "Збережено") {
    if (mutationInFlight.current) return false;
    mutationInFlight.current = true;
    setBusy(true);
    setError("");
    try {
      try {
        await work();
      } catch (e) {
        fail(e);
        await load().catch(() => {});
        return false;
      }
      setNotice(message);
      // A failed refresh must not make a committed mutation look unsuccessful.
      await load().catch(() =>
        setError(
          "Збережено, але оновити екран не вдалося. Оновіть сторінку; повторювати запис не потрібно.",
        ),
      );
      return true;
    } finally {
      mutationInFlight.current = false;
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", "POST");
      loadGeneration.current += 1;
      setModal(null);
      setObservation(null);
      setSchedules([]);
      setCsrf("");
      setUser(null);
      setPlans([]);
      setTransactions([]);
      setJobs([]);
      setSnapshot({ version: 0, snapshot: null, calculation: null });
    } catch (e) {
      fail(e);
    }
  }
  if (!ready)
    return (
      <main className="splash">
        <Brand />
        <p>Відкриваємо ваш простір…</p>
      </main>
    );
  if (!user)
    return (
      <LoginScreen
        onLogin={(u) => {
          setCsrf(u.csrf_token);
          setUser(u);
          setError("");
        }}
      />
    );
  const calc = snapshot.calculation,
    data = snapshot.snapshot;
  const active = plans.filter((p) => p.status === "active");
  const pending = jobs.filter((j) =>
    ["queued", "running"].includes(j.status),
  ).length;
  const planned = calc?.planned_limit_minor;
  const totalCommitments =
    data?.commitments?.reduce((a, c) => a + c.amount_minor, 0) || 0;
  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">ОСОБИСТИЙ ПРОСТІР</div>
        <nav aria-label="Основна навігація">
          {(Object.keys(titles) as Page[]).map((p) => (
            <button
              key={p}
              className={page === p ? "nav-item selected" : "nav-item"}
              onClick={() => setPage(p)}
            >
              <Icon name={p} />
              <span>{titles[p]}</span>
              {p === "plans" && active.length > 0 && (
                <span className="nav-count">{active.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="avatar">М</span>
          <div>
            <b>Мій простір</b>
            <small>Особистий alpha-доступ</small>
          </div>
          <button className="icon-button" aria-label="Вийти" onClick={logout}>
            <Icon name="logout" />
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="mobile-brand">
            <Brand />
          </div>
          <span className="breadcrumb">
            Мій простір <span>/</span> {titles[page]}
          </span>
          <span className="today">
            {new Date().toLocaleDateString("uk-UA", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
        </header>
        <div className="content">
          {!online && (
            <div className="alert warning" role="status">
              Немає з’єднання. Показані дані можуть бути застарілими. Записи й
              підтвердження доступні після підключення.
            </div>
          )}
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button
                className="icon-button"
                onClick={() => setError("")}
                aria-label="Закрити помилку"
              >
                <Icon name="close" />
              </button>
            </div>
          )}
          <div className="page-heading">
            <div>
              <p className="eyebrow">ВАШІ ГРОШІ. ВАШІ РІШЕННЯ.</p>
              <h1>{titles[page]}</h1>
              <p>
                {page === "now"
                  ? "Ясність сьогодні. Більше можливостей завтра."
                  : page === "plans"
                    ? "Збережіть важливе. Змініть спосіб витрачати."
                    : page === "movement"
                      ? "Покупки, надходження та їхнє призначення."
                      : page === "earn"
                        ? "Наступний крок до потрібного доходу."
                        : "Підключення, дані та робота у фоні."}
              </p>
            </div>
            <div className="heading-actions">
              {page === "now" && (
                <button
                  className="button secondary"
                  onClick={() => setModal("snapshot")}
                  disabled={!online}
                >
                  <Icon name="refresh" />
                  Оновити кошти
                </button>
              )}
              {page === "plans" && (
                <button
                  className="button"
                  onClick={() => setModal("plan")}
                  disabled={!online}
                >
                  <Icon name="plus" />
                  Новий план
                </button>
              )}
              {page === "movement" && (
                <>
                  <button
                    className="button secondary"
                    onClick={() => setModal("import")}
                    disabled={!online}
                  >
                    Імпорт CSV
                  </button>
                  <button
                    className="button"
                    onClick={() => setModal("transaction")}
                    disabled={!online}
                  >
                    <Icon name="plus" />
                    Додати запис
                  </button>
                </>
              )}
            </div>
          </div>
          {page === "now" && (
            <>
              <div className="dashboard-grid">
                <section className="balance-card">
                  <div className="balance-top">
                    <span>Можна витратити зараз</span>
                    <span className="pill translucent">
                      {!online
                        ? "Без з’єднання"
                        : calc?.decision === "UNKNOWN"
                          ? "Потрібне оновлення"
                          : data
                            ? "Ручні дані"
                            : "Почнімо з залишку"}
                    </span>
                  </div>
                  <div className="balance-value">{money(planned)}</div>
                  <p>
                    {data
                      ? `Після зобов’язань, життя, резерву й цілі. Горизонт — ${data.horizon_days} днів.`
                      : "Додайте залишок, найближчі платежі та ваш резерв."}
                  </p>
                  <div className="balance-rule" />
                  <div className="balance-bottom">
                    <div>
                      <small>Межа без урахування цілі</small>
                      <strong>{money(calc?.essential_limit_minor)}</strong>
                    </div>
                    <button
                      className="button lime"
                      disabled={!online}
                      onClick={() => setModal(data ? "spend" : "snapshot")}
                    >
                      {data ? "Перевірити покупку" : "Додати мої кошти"}
                      <Icon name="arrow" />
                    </button>
                  </div>
                </section>
                <section className="card next-card">
                  <div className="section-label">
                    <span className="number-label">01</span>НАСТУПНИЙ КРОК
                  </div>
                  <h2>
                    {!data
                      ? "Знати свій справжній залишок"
                      : active.length
                        ? "Ваш план уже в русі"
                        : "Маленька зміна. Відчутний результат."}
                  </h2>
                  <p>
                    {!data
                      ? "Банківський залишок — лише початок. Врахуйте те, що ще має бути оплачено."
                      : active.length
                        ? `«${active[0].title}»: запишіть фактичну покупку й порівняйте її зі звичним способом.`
                        : "Почніть з однієї повторюваної покупки. Порівняйте альтернативу без відмови від того, що любите."}
                  </p>
                  <button
                    className="text-button"
                    onClick={() =>
                      !data ? setModal("snapshot") : setPage("plans")
                    }
                  >
                    {!data ? "Заповнити дані" : "До моїх планів"}
                    <Icon name="arrow" />
                  </button>
                </section>
              </div>
              <div className="stats-grid">
                {[
                  {
                    label: "Зараз на рахунках",
                    value: data?.balance_minor,
                    sub: "Власні кошти за вашим записом",
                  },
                  {
                    label: "Зобов’язання",
                    value: data ? totalCommitments : null,
                    sub: "Усі внесені неоплачені платежі",
                  },
                  {
                    label: "Резерв",
                    value: data?.reserve_minor,
                    sub: "Захищений запас",
                  },
                  {
                    label: "Моя ціль",
                    value: data?.goal_minor,
                    sub: "Внесок у межах горизонту",
                  },
                ].map((s, i) => (
                  <section className="card stat" key={s.label}>
                    <div className="stat-top">
                      <span>{s.label}</span>
                      <span className="stat-index">0{i + 1}</span>
                    </div>
                    <strong>{money(s.value)}</strong>
                    <small>{s.sub}</small>
                  </section>
                ))}
              </div>
              {calc && (
                <div className="calculation-note">
                  <Icon name="check" />
                  <span>
                    {calc.basis === "cash_only"
                      ? "Розрахунок із поточних коштів."
                      : "Умовний прогноз із підтвердженими майбутніми доходами."}{" "}
                    {calc.warnings.length > 0
                      ? "Є припущення або платежі поза горизонтом — перегляньте деталі."
                      : ""}
                  </span>
                  <details>
                    <summary>Основа розрахунку</summary>
                    <p>
                      Оновлено:{" "}
                      {calc.as_of
                        ? new Date(calc.as_of).toLocaleString("uk-UA")
                        : "немає даних"}
                      . До {calc.horizon_end}. Майбутні доходи не є отриманими
                      грошима. Розрахунок використовує календар UTC і спільний
                      залишок рахунків.
                    </p>
                    {calc.missing_inputs.length > 0 && (
                      <p>
                        Неповні чи застарілі поля:{" "}
                        {calc.missing_inputs.join(", ")}
                      </p>
                    )}
                    {calc.commitments_beyond_horizon.length > 0 && (
                      <p>
                        Поза горизонтом:{" "}
                        {calc.commitments_beyond_horizon.join(", ")}
                      </p>
                    )}
                    <small>Політика {calc.policy_version}</small>
                  </details>
                </div>
              )}
              <div className="bottom-grid">
                <section className="card">
                  <div className="section-head">
                    <h2>Найближчі платежі</h2>
                    <button
                      className="text-button"
                      onClick={() => setModal("snapshot")}
                    >
                      Змінити
                    </button>
                  </div>
                  {data?.commitments?.length ? (
                    <div className="list">
                      {[...data.commitments]
                        .sort((a, b) => a.due_date.localeCompare(b.due_date))
                        .slice(0, 5)
                        .map((c) => (
                          <div className="list-row" key={c.id}>
                            <span className="row-icon">
                              <Icon name="plans" />
                            </span>
                            <div className="row-main">
                              <b>{c.label}</b>
                              <small>{c.due_date}</small>
                            </div>
                            <strong>{money(c.amount_minor)}</strong>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <div className="quiet-empty">
                      Поки немає внесених платежів.
                      <br />
                      Додайте їх, щоб залишок був змістовним.
                    </div>
                  )}
                </section>
                <section className="card">
                  <div className="section-head">
                    <h2>У фокусі</h2>
                    <span className="pill">{active.length} активних</span>
                  </div>
                  {active.length ? (
                    active.slice(0, 3).map((p) => (
                      <div className="list-row" key={p.id}>
                        <span className="row-icon mint">
                          <Icon name="plans" />
                        </span>
                        <div className="row-main">
                          <b>{p.title}</b>
                          <small>Потенціал на місяць</small>
                        </div>
                        <strong className="positive">
                          {money(p.scenario_savings_minor)}
                        </strong>
                      </div>
                    ))
                  ) : (
                    <div className="quiet-empty">
                      Планів ще немає.
                      <br />
                      Першу зміну можна зробити зовсім невеликою.
                    </div>
                  )}
                  <button
                    className="text-button"
                    onClick={() => setPage("plans")}
                  >
                    Відкрити плани
                    <Icon name="arrow" />
                  </button>
                </section>
              </div>
            </>
          )}
          {page === "plans" && (
            <>
              {plans.length ? (
                <div className="plans-grid">
                  {plans.map((p) => (
                    <section className="card plan-card" key={p.id}>
                      <div className="plan-top">
                        <span className={"pill " + p.status}>
                          {states[p.status]}
                        </span>
                        <span className="muted">
                          {p.frequency_per_month} разів / місяць
                        </span>
                      </div>
                      <h2>{p.title}</h2>
                      <p>{p.need || "Зберегти потребу, змінити спосіб."}</p>
                      <div className="comparison">
                        <div>
                          <small>Звичний спосіб</small>
                          <strong>{money(p.baseline_minor)}</strong>
                        </div>
                        <Icon name="arrow" />
                        <div>
                          <small>Альтернатива</small>
                          <strong>{money(p.alternative_minor)}</strong>
                        </div>
                      </div>
                      <div className="plan-saving">
                        <span>Потенціал / місяць</span>
                        <strong>{money(p.scenario_savings_minor)}</strong>
                      </div>
                      <p className="fine">
                        Перший місяць: {money(p.first_month_savings_minor)} з
                        урахуванням стартових витрат. Це сценарій, не отриманий
                        дохід.
                      </p>
                      {p.observations.length > 0 && (
                        <div className="observed">
                          <b>{p.observations.length} порівнюваних випадків</b>
                          <span>Витрачено {money(p.observed_spend_minor)}</span>
                          <span>
                            Різниця зі звичним способом:{" "}
                            {money(p.observed_difference_minor)}
                          </span>
                        </div>
                      )}
                      <div className="plan-actions">
                        {p.status === "proposed" && (
                          <>
                            <button
                              className="button"
                              disabled={busy || !online}
                              onClick={() =>
                                action(
                                  () =>
                                    api("/plans/" + p.id, "PATCH", {
                                      expected_version: p.version,
                                      status: "active",
                                    }),
                                  "План активовано",
                                )
                              }
                            >
                              Спробувати
                            </button>
                            <button
                              className="button secondary"
                              disabled={busy || !online}
                              onClick={() =>
                                action(
                                  () =>
                                    api("/plans/" + p.id, "PATCH", {
                                      expected_version: p.version,
                                      status: "rejected",
                                      rejection_reason: "Не підходить",
                                    }),
                                  "Ваш вибір збережено",
                                )
                              }
                            >
                              Не підходить
                            </button>
                          </>
                        )}
                        {p.status === "active" && (
                          <>
                            <button
                              className="button"
                              onClick={() => setObservation(p)}
                              disabled={!online}
                            >
                              Записати результат
                            </button>
                            <button
                              className="button secondary"
                              disabled={busy || !online}
                              onClick={() =>
                                action(
                                  () =>
                                    api("/plans/" + p.id, "PATCH", {
                                      expected_version: p.version,
                                      status: "completed",
                                    }),
                                  "План завершено",
                                )
                              }
                            >
                              Завершити
                            </button>
                          </>
                        )}
                        {["rejected", "completed"].includes(p.status) && (
                          <button
                            className="button secondary"
                            disabled={busy || !online}
                            onClick={() =>
                              action(
                                () =>
                                  api("/plans/" + p.id, "PATCH", {
                                    expected_version: p.version,
                                    status: "active",
                                  }),
                                "План поновлено",
                              )
                            }
                          >
                            Поновити план
                          </button>
                        )}
                      </div>
                      <button
                        className="text-button"
                        disabled={busy || !online}
                        onClick={() =>
                          action(
                            () =>
                              api("/jobs", "POST", {
                                kind: "compare_plan",
                                provider: "manual",
                                payload: {
                                  title: p.title,
                                  need: p.need,
                                  baseline_minor: p.baseline_minor,
                                  alternative_minor: p.alternative_minor,
                                  frequency_per_month: p.frequency_per_month,
                                  setup_cost_minor: p.setup_cost_minor,
                                  currency: "EUR",
                                },
                                idempotency_key: crypto.randomUUID(),
                              }),
                            "Фонове порівняння в черзі",
                          )
                        }
                      >
                        Порахувати у фоні
                        <Icon name="arrow" />
                      </button>
                      {p.status === "active" && (
                        <button
                          className="text-button"
                          disabled={
                            busy ||
                            !online ||
                            schedules.some((s) => s.plan_id === p.id)
                          }
                          onClick={() =>
                            action(
                              () =>
                                api("/schedules", "POST", {
                                  plan_id: p.id,
                                  interval_hours: 24,
                                }),
                              "Щоденний розрахунок увімкнено",
                            )
                          }
                        >
                          {schedules.some((s) => s.plan_id === p.id)
                            ? "Щоденний розрахунок увімкнено"
                            : "Перераховувати щодня"}
                        </button>
                      )}
                    </section>
                  ))}
                </div>
              ) : (
                <Empty
                  title="Один план — уже початок"
                  text="Наприклад, сок на роботу: той самий результат, інша ціна за порцію. Порівняйте витрати й перевірте зручність на практиці."
                >
                  <button className="button" onClick={() => setModal("plan")}>
                    Створити перший план
                  </button>
                </Empty>
              )}
            </>
          )}
          {page === "movement" && (
            <>
              <div className="alert neutral">
                Журнал і CSV не змінюють залишок автоматично: покупка вже могла
                бути врахована банком. Після звірки оновіть кошти на екрані
                «Зараз».
              </div>
              {transactions.length ? (
                <section className="card">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Операція</th>
                          <th>Дата</th>
                          <th>Категорія</th>
                          <th className="align-right">Сума</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((t) => (
                          <tr key={t.id}>
                            <td>
                              <b>{t.description}</b>
                            </td>
                            <td>{t.date}</td>
                            <td>
                              <span className="pill">
                                {t.category === "uncategorized"
                                  ? "Без категорії"
                                  : t.category}
                              </span>
                            </td>
                            <td
                              className={
                                "align-right amount " +
                                (t.amount_minor > 0 ? "positive" : "")
                              }
                            >
                              {money(t.amount_minor)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ) : (
                <Empty
                  title="Перші записи з’являться тут"
                  text="Додайте витрату вручну або імпортуйте CSV. Повторний імпорт того самого рядка не створить другу операцію."
                >
                  <button
                    className="button"
                    onClick={() => setModal("transaction")}
                  >
                    Додати запис
                  </button>
                </Empty>
              )}
            </>
          )}
          {page === "earn" && (
            <Earn
              providers={providers}
              busy={busy}
              online={online}
              onSubmit={(body) =>
                action(
                  () =>
                    api("/jobs", "POST", {
                      ...body,
                      idempotency_key: crypto.randomUUID(),
                    }),
                  "Завдання поставлено в чергу",
                )
              }
            />
          )}
          {page === "settings" && (
            <div className="settings-grid">
              <section className="card">
                <h2>Моделі та підключення</h2>
                <p>
                  Моделі допомагають із варіантами й чернетками. Фінансовий
                  розрахунок працює без них.
                </p>
                {providers.items.map((p) => (
                  <div className="list-row" key={p.id}>
                    <div className="row-main">
                      <b>{p.name}</b>
                      <small>
                        {p.model ||
                          (p.id === "manual"
                            ? "Розрахунки та посилання пошуку"
                            : "Налаштовується на сервері")}
                      </small>
                    </div>
                    <span className={"pill " + (p.available ? "active" : "")}>
                      {p.available ? "Доступно" : "Не підключено"}
                    </span>
                  </div>
                ))}
                <p className="fine">
                  Виклики платних моделей:{" "}
                  {providers.metered_inference_enabled
                    ? "дозволені оператором"
                    : "вимкнені"}
                  . Ліміт: {providers.daily_job_limit} завдань за добу.
                </p>
                <div className="alert neutral">
                  Банки, автоматичний пошук живих вакансій, зовнішня відправка
                  та MCP OAuth ще не підключені.
                </div>
              </section>
              <section className="card">
                <h2>Ваші дані</h2>
                <p>
                  Поточний alpha-доступ має одного власника. Дані й задачі
                  зберігаються на сервері.
                </p>
                <button
                  className="button secondary full"
                  onClick={async () => {
                    try {
                      const data = await api("/export");
                      const url = URL.createObjectURL(
                        new Blob([JSON.stringify(data, null, 2)], {
                          type: "application/json",
                        }),
                      );
                      const link = document.createElement("a");
                      link.href = url;
                      link.download = "mozhna-export.json";
                      link.click();
                      setTimeout(() => URL.revokeObjectURL(url), 1000);
                    } catch (e) {
                      fail(e);
                    }
                  }}
                >
                  Експортувати JSON
                </button>
                <button
                  className="button danger full"
                  onClick={() => setModal("delete")}
                >
                  Видалити мої дані
                </button>
                <p className="fine">
                  Видалення очищає простір і завершує всі ваші сесії. Уже
                  надіслані провайдеру запити відкликати неможливо.
                </p>
              </section>
            </div>
          )}
          {page === "settings" && (
            <section className="card jobs-card">
              <h2>Розклад планів</h2>
              <p>
                Сервер повторює арифметичне порівняння за вашим інтервалом,
                навіть коли пристрої закриті. Нові ціни автоматично не шукає.
              </p>
              {schedules.length ? (
                schedules.map((s) => (
                  <div className="list-row" key={s.id}>
                    <div className="row-main">
                      <b>
                        {plans.find((p) => p.id === s.plan_id)?.title || "План"}
                      </b>
                      <small>
                        Кожні {s.interval_hours} год. · Наступний запуск{" "}
                        {new Date(s.next_due * 1000).toLocaleString("uk-UA")}
                      </small>
                    </div>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        action(
                          () => api("/schedules/" + s.id, "DELETE"),
                          "Розклад вимкнено",
                        )
                      }
                    >
                      Вимкнути
                    </button>
                  </div>
                ))
              ) : (
                <p className="fine">
                  Увімкніть щоденний розрахунок в активному плані.
                </p>
              )}
            </section>
          )}
          {(page === "settings" || page === "earn" || pending > 0) && (
            <section className="card jobs-card">
              <div className="section-head">
                <div>
                  <h2>Робота у фоні</h2>
                  <p className="fine">
                    Можна закрити пристрій. Задачі виконує окремий серверний
                    worker.
                  </p>
                </div>
                <span className="pill">{pending} у роботі</span>
              </div>
              {jobs.length ? (
                jobs.slice(0, 10).map((j) => (
                  <div className="job-row" key={j.id}>
                    <div className="job-info">
                      <span className={"pill " + j.status}>
                        {states[j.status] || j.status}
                      </span>
                      <b>
                        {j.kind === "compare_plan"
                          ? "Порівняння плану"
                          : j.kind === "income_search"
                            ? "Напрямки пошуку"
                            : "Чернетка відгуку"}
                      </b>
                      <small>
                        {new Date(j.created_at).toLocaleString("uk-UA")} ·{" "}
                        {j.provider}
                      </small>
                      {j.error && <p className="error-text">{j.error}</p>}
                      {j.result && <JobResult result={j.result} />}
                    </div>
                    {["queued", "running"].includes(j.status) && (
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          action(
                            () => api("/jobs/" + j.id + "/cancel", "POST"),
                            "Подальші кроки скасовано",
                          )
                        }
                      >
                        Скасувати
                      </button>
                    )}
                  </div>
                ))
              ) : (
                <div className="quiet-empty">Нових завдань немає.</div>
              )}
            </section>
          )}
          <footer className="footer">
            <span>Можна · alpha 0.1</span>
            <span>Ваші рішення залишаються вашими.</span>
          </footer>
        </div>
      </main>
      <nav className="mobile-nav" aria-label="Мобільна навігація">
        {(Object.keys(titles) as Page[]).map((p) => (
          <button
            key={p}
            className={page === p ? "selected" : ""}
            onClick={() => setPage(p)}
            aria-label={titles[p]}
          >
            <Icon name={p} />
            <span>
              {p === "movement"
                ? "Рух"
                : p === "earn"
                  ? "Дохід"
                  : p === "settings"
                    ? "Простір"
                    : titles[p]}
            </span>
          </button>
        ))}
      </nav>
      {notice && (
        <div className="toast" role="status">
          <Icon name="check" />
          {notice}
        </div>
      )}
      {modal === "snapshot" && (
        <SnapshotEditor
          value={data}
          version={snapshot.version}
          onClose={() => setModal(null)}
          onSave={async (body) => {
            if (
              await action(
                () => api("/snapshot", "PUT", body),
                "Кошти оновлено",
              )
            )
              setModal(null);
          }}
        />
      )}
      {modal === "spend" && <Spend onClose={() => setModal(null)} />}
      {modal === "plan" && (
        <PlanEditor
          onClose={() => setModal(null)}
          onSave={async (body) => {
            if (
              await action(() => api("/plans", "POST", body), "План створено")
            )
              setModal(null);
          }}
        />
      )}
      {modal === "transaction" && (
        <TransactionEditor
          onClose={() => setModal(null)}
          onSave={async (body) => {
            if (
              await action(
                () => api("/transactions", "POST", body),
                "Запис додано; звірте залишок",
              )
            )
              setModal(null);
          }}
        />
      )}
      {modal === "import" && (
        <ImportEditor
          onClose={() => setModal(null)}
          onSave={async (csv) => {
            let result: { added: number; skipped: number } | undefined;
            if (
              await action(async () => {
                result = await api("/transactions/import", "POST", {
                  csv_text: csv,
                  currency: "EUR",
                });
              }, "Імпорт завершено")
            ) {
              setModal(null);
              setNotice(
                `Додано ${result?.added}, пропущено дублів ${result?.skipped}`,
              );
            }
          }}
        />
      )}
      {observation && (
        <ObservationEditor
          plan={observation}
          onClose={() => setObservation(null)}
          onSave={async (body) => {
            if (
              await action(
                () =>
                  api(
                    "/plans/" + observation.id + "/observations",
                    "POST",
                    body,
                  ),
                "Результат збережено",
              )
            )
              setObservation(null);
          }}
        />
      )}
      {modal === "delete" && (
        <Modal title="Видалити всі мої дані?" onClose={() => setModal(null)}>
          <p>
            Залишок, плани, записи й задачі буде видалено. Експортуйте їх перед
            продовженням.
          </p>
          <button
            className="button danger full"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api("/data", "DELETE", { confirmation: "DELETE" });
                loadGeneration.current += 1;
                setModal(null);
                setObservation(null);
                setSchedules([]);
                setUser(null);
                setCsrf("");
                setSnapshot({ version: 0, snapshot: null, calculation: null });
                setPlans([]);
                setJobs([]);
                setTransactions([]);
              } catch (e) {
                fail(e);
              } finally {
                setBusy(false);
              }
            }}
          >
            Так, видалити й вийти
          </button>
        </Modal>
      )}
    </div>
  );
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">м</span>
      <span>
        можна<span className="brand-dot">.</span>
      </span>
    </div>
  );
}
function LoginScreen({ onLogin }: { onLogin: (u: Auth) => void }) {
  const [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await api<Auth>("/auth/login", "POST", { password }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не вдалося увійти");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-layout">
      <section className="login-story">
        <Brand />
        <div>
          <p className="eyebrow">МІСЦЕ ДЛЯ ВАШИХ ПЛАНІВ</p>
          <h1>
            Знати, що можна.
            <br />
            <em>Обирати своє.</em>
          </h1>
          <p>
            Кошти сьогодні, продумані зміни й наступний крок — в одному
            особистому просторі.
          </p>
        </div>
        <span className="login-foot">Ваші гроші. Ваші рішення.</span>
      </section>
      <section className="login-form">
        <div className="login-box">
          <span className="pill">MOZHNA ALPHA</span>
          <h2>З поверненням</h2>
          <p>Увійдіть до свого простору з паролем власника.</p>
          <form onSubmit={submit}>
            <Field label="Пароль">
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
            </Field>
            {error && (
              <p className="error-text" role="alert">
                {error}
              </p>
            )}
            <button className="button full" disabled={busy}>
              {busy ? "Входимо…" : "Увійти"}
              <Icon name="arrow" />
            </button>
          </form>
          <p className="fine">
            Пароль задається під час налаштування сервера. Дані не зберігаються
            в пам’яті моделі.
          </p>
        </div>
      </section>
    </main>
  );
}

function SnapshotEditor({
  value,
  version,
  onClose,
  onSave,
}: {
  value: Snapshot | null;
  version: number;
  onClose: () => void;
  onSave: (s: Schema["SnapshotUpdate"]) => Promise<void>;
}) {
  const [editingVersion] = useState(version);
  const [balance, setBalance] = useState(euros(value?.balance_minor)),
    [reserve, setReserve] = useState(euros(value?.reserve_minor) || "0"),
    [goal, setGoal] = useState(euros(value?.goal_minor) || "0"),
    [living, setLiving] = useState(euros(value?.living_budget_minor) || "0"),
    [horizon, setHorizon] = useState(value?.horizon_days || 30);
  type Flow = {
    id: string;
    label: string;
    amount: string;
    due_date: string;
    confirmed?: boolean;
  };
  const [flows, setFlows] = useState<Flow[]>(
      (value?.commitments || []).map((c) => ({
        ...c,
        amount: euros(c.amount_minor),
      })),
    ),
    [incomes, setIncomes] = useState<Flow[]>(
      (value?.incomes || []).map((c) => ({
        ...c,
        amount: euros(c.amount_minor),
      })),
    );
  const [confirmed, setConfirmed] = useState(false),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  function renderFlows(
    list: Flow[],
    set: (list: Flow[]) => void,
    income = false,
  ) {
    return (
      <>
        <div className="form-section">
          <h3>{income ? "Майбутні доходи" : "Неоплачені зобов’язання"}</h3>
          <button
            type="button"
            className="text-button"
            onClick={() =>
              set([
                ...list,
                {
                  id: crypto.randomUUID(),
                  label: "",
                  amount: "",
                  due_date: today(),
                  confirmed: false,
                },
              ])
            }
          >
            <Icon name="plus" />
            Додати
          </button>
        </div>
        {list.map((c, i) => (
          <div className="flow-row" key={c.id}>
            <input
              aria-label="Назва"
              placeholder={income ? "Зарплата" : "Оренда"}
              required
              value={c.label}
              onChange={(e) =>
                set(
                  list.map((v, n) =>
                    n === i ? { ...v, label: e.target.value } : v,
                  ),
                )
              }
            />
            <input
              aria-label="Сума в євро"
              placeholder="€ 0,00"
              inputMode="decimal"
              required
              value={c.amount}
              onChange={(e) =>
                set(
                  list.map((v, n) =>
                    n === i ? { ...v, amount: e.target.value } : v,
                  ),
                )
              }
            />
            <input
              aria-label="Дата"
              type="date"
              required
              value={c.due_date}
              onChange={(e) =>
                set(
                  list.map((v, n) =>
                    n === i ? { ...v, due_date: e.target.value } : v,
                  ),
                )
              }
            />
            <button
              type="button"
              className="icon-button"
              aria-label="Видалити платіж"
              onClick={() => set(list.filter((_, n) => n !== i))}
            >
              <Icon name="close" />
            </button>
            {income && (
              <label className="checkbox flow-confirm">
                <input
                  type="checkbox"
                  checked={c.confirmed || false}
                  onChange={(e) =>
                    set(
                      list.map((v, n) =>
                        n === i ? { ...v, confirmed: e.target.checked } : v,
                      ),
                    )
                  }
                />
                Графік підтверджено мною
              </label>
            )}
          </div>
        ))}
      </>
    );
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const transform = (f: Flow) => ({
        id: f.id,
        label: f.label,
        amount_minor: cents(f.amount),
        due_date: f.due_date,
      });
      await onSave({
        expected_version: editingVersion,
        snapshot: {
          balance_minor: cents(balance),
          currency: "EUR",
          as_of: new Date().toISOString(),
          horizon_days: Number(horizon),
          reserve_minor: cents(reserve),
          goal_minor: cents(goal),
          living_budget_minor: cents(living),
          commitments: flows.map(transform),
          incomes: incomes.map((f) => ({
            ...transform(f),
            confirmed: f.confirmed || false,
          })),
          data_complete: confirmed,
        },
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal title="Мої кошти та зобов’язання" onClose={onClose}>
      <p>
        Якщо дані змінено на іншому пристрої, закрийте й відкрийте форму знову.
        Внесіть власні кошти без кредитного ліміту. Уже оплачені витрати не
        додавайте вдруге.
      </p>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Залишок зараз, €">
            <input
              inputMode="decimal"
              value={balance}
              required
              onChange={(e) => setBalance(e.target.value)}
            />
          </Field>
          <Field label="Резерв, €">
            <input
              inputMode="decimal"
              value={reserve}
              required
              onChange={(e) => setReserve(e.target.value)}
            />
          </Field>
          <Field
            label="Залишилось на звичайне життя, €"
            hint="Майбутні продукти, транспорт та інше"
          >
            <input
              inputMode="decimal"
              value={living}
              required
              onChange={(e) => setLiving(e.target.value)}
            />
          </Field>
          <Field label="Внесок у ціль, €">
            <input
              inputMode="decimal"
              value={goal}
              required
              onChange={(e) => setGoal(e.target.value)}
            />
          </Field>
        </div>
        <Field label="Горизонт, днів">
          <input
            type="number"
            min="1"
            max="366"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          />
        </Field>
        {renderFlows(flows, setFlows)}
        {renderFlows(incomes, setIncomes, true)}
        <p className="fine">
          Майбутні доходи — припущення, не поточні гроші. Дати розраховуються за
          календарем UTC. Доходи сьогодні й раніше мають уже входити в звірений
          залишок.
        </p>
        <label className="checkbox">
          <input
            type="checkbox"
            required
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          Я звірив(-ла) залишок та вніс(-ла) відомі витрати й доходи.
        </label>
        {error && <p className="error-text">{error}</p>}
        <div className="form-footer">
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              setBalance("1000");
              setReserve("200");
              setLiving("100");
              setGoal("50");
              setFlows([
                {
                  id: "demo-rent",
                  label: "Оренда (приклад)",
                  amount: "600",
                  due_date: today(),
                },
              ]);
              setIncomes([]);
              setConfirmed(false);
            }}
          >
            Заповнити приклад
          </button>
          <button className="button" disabled={saving}>
            {saving ? "Збереження…" : "Зберегти кошти"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Spend({ onClose }: { onClose: () => void }) {
  const [amount, setAmount] = useState(""),
    [result, setResult] = useState<Calculation | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(
        await api<Calculation>("/simulate", "POST", {
          amount_minor: cents(amount),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Чи можна цю покупку?" onClose={onClose}>
      <form onSubmit={submit}>
        <Field label="Вартість покупки, €">
          <input
            className="spend-input"
            inputMode="decimal"
            autoFocus
            placeholder="0,00"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
              setResult(null);
            }}
            required
          />
        </Field>
        <button className="button full" disabled={busy}>
          {busy ? "Рахуємо…" : "Перевірити"}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className={"decision " + result.decision}>
          <h2>{decisionNames[result.decision]}</h2>
          <p>{decisionText[result.decision]}</p>
          {result.decision !== "UNKNOWN" && (
            <dl>
              <div>
                <dt>Запас після покупки з урахуванням цілі</dt>
                <dd>{money(result.planned_headroom_minor)}</dd>
              </div>
              <div>
                <dt>Запас після покупки без цілі</dt>
                <dd>{money(result.essential_headroom_minor)}</dd>
              </div>
            </dl>
          )}
          <small>
            До {result.horizon_end}.{" "}
            {result.basis === "cash_only"
              ? "Без майбутніх доходів."
              : "З урахуванням умовного графіка доходів."}{" "}
            Перевірка не списує гроші.
          </small>
        </div>
      )}
    </Modal>
  );
}

function PlanEditor({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (p: Schema["PlanCreate"]) => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await onSave({
        title: String(f.get("title")),
        need: String(f.get("need")),
        baseline_minor: cents(String(f.get("baseline"))),
        alternative_minor: cents(String(f.get("alternative"))),
        frequency_per_month: Number(f.get("frequency")),
        setup_cost_minor: cents(String(f.get("setup"))),
        currency: "EUR",
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="План маленької зміни" onClose={onClose}>
      <p>
        Порівнюйте однакову порцію або одну й ту саму потребу. Наприклад, 200 мл
        соку на роботу.
      </p>
      <form onSubmit={submit}>
        <Field label="Назва">
          <input
            name="title"
            required
            maxLength={200}
            placeholder="Сок на роботу"
          />
        </Field>
        <Field label="Що важливо зберегти">
          <textarea
            name="need"
            maxLength={2000}
            placeholder="Смак, зручність, можливість зберігати…"
          />
        </Field>
        <div className="form-grid">
          <Field label="Звична ціна за випадок, €">
            <input
              name="baseline"
              required
              inputMode="decimal"
              placeholder="1,50"
            />
          </Field>
          <Field label="Альтернатива за той самий обсяг, €">
            <input
              name="alternative"
              required
              inputMode="decimal"
              placeholder="0,50"
            />
          </Field>
          <Field label="Кількість випадків за місяць">
            <input
              name="frequency"
              type="number"
              min={1}
              max={1000}
              defaultValue={20}
              required
            />
          </Field>
          <Field label="Додаткові стартові витрати, €">
            <input name="setup" inputMode="decimal" defaultValue="0" required />
          </Field>
        </div>
        <p className="fine">
          Ціни вводите ви. Перш ніж почати, перевірте доступність коштів на
          упаковку, зберігання й зручність. Цей план не купує нічого
          автоматично.
        </p>
        {error && <p className="error-text">{error}</p>}
        <button className="button full" disabled={busy}>
          Зберегти пропозицію
        </button>
      </form>
    </Modal>
  );
}

function TransactionEditor({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (t: Schema["TransactionCreate"]) => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const amount = cents(String(f.get("amount")));
      if (amount < 0)
        throw new Error("Введіть додатну суму; напрямок оберіть окремо.");
      await onSave({
        date: String(f.get("date")),
        description: String(f.get("description")),
        amount_minor: amount * (f.get("kind") === "expense" ? -1 : 1),
        category: String(f.get("category")),
        currency: "EUR",
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Новий запис" onClose={onClose}>
      <form onSubmit={submit}>
        <Field label="Опис">
          <input
            name="description"
            required
            maxLength={500}
            placeholder="Покупка в магазині"
          />
        </Field>
        <div className="form-grid">
          <Field label="Сума, €">
            <input name="amount" inputMode="decimal" required />
          </Field>
          <Field label="Напрямок">
            <select name="kind">
              <option value="expense">Витрата</option>
              <option value="income">Надходження</option>
            </select>
          </Field>
          <Field label="Дата">
            <input name="date" type="date" required defaultValue={today()} />
          </Field>
          <Field label="Категорія">
            <select name="category">
              <option>Продукти</option>
              <option>Транспорт</option>
              <option>Житло</option>
              <option>Дохід</option>
              <option>Інше</option>
            </select>
          </Field>
        </div>
        <p className="fine">
          Запис додається в журнал. Залишок на рахунках оновлюється окремо після
          звірки.
        </p>
        {error && <p className="error-text">{error}</p>}
        <button className="button full" disabled={busy}>
          Додати запис
        </button>
      </form>
    </Modal>
  );
}
function ImportEditor({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (csv: string) => Promise<void>;
}) {
  const [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <Modal title="Імпорт операцій з CSV" onClose={onClose}>
      <p>
        Колонки: date, description, amount_minor. Сума — цілі центи: −150
        означає витрату €1,50. Додатково: category, external_id.
      </p>
      <Field label="Оберіть CSV-файл">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            if (file.size > 2000000) {
              setError("Файл перевищує 2 МБ");
              return;
            }
            setText(await file.text());
          }}
        />
      </Field>
      <Field label="Або вставте CSV">
        <textarea
          rows={7}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            "date,description,amount_minor,external_id\n2026-09-07,Сік,-150,purchase-1"
          }
        />
      </Field>
      <p className="fine">
        До 1000 рядків. Однакові покупки без різних external_id вважаються
        дублями. Імпорт не змінює залишок.
      </p>
      {error && <p className="error-text">{error}</p>}
      <button
        className="button full"
        disabled={busy || !text}
        onClick={async () => {
          setBusy(true);
          try {
            await onSave(text);
          } finally {
            setBusy(false);
          }
        }}
      >
        Імпортувати записи
      </button>
    </Modal>
  );
}
function ObservationEditor({
  plan,
  onClose,
  onSave,
}: {
  plan: Plan;
  onClose: () => void;
  onSave: (o: Schema["Observation"]) => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <Modal title="Як пройшло насправді?" onClose={onClose}>
      <p>
        «{plan.title}». Запишіть витрати за один порівнюваний випадок — той
        самий обсяг, що у плані.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setBusy(true);
          try {
            await onSave({
              amount_minor: cents(String(f.get("amount"))),
              date: String(f.get("date")),
              note: String(f.get("note")),
            });
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="form-grid">
          <Field label="Фактично витрачено, €">
            <input name="amount" inputMode="decimal" required />
          </Field>
          <Field label="Дата">
            <input name="date" type="date" defaultValue={today()} required />
          </Field>
        </div>
        <Field label="Зручність, смак, відходи чи інше">
          <textarea
            name="note"
            placeholder="Чи зберегли ви те, що хотіли?"
            maxLength={2000}
          />
        </Field>
        {error && <p className="error-text">{error}</p>}
        <button className="button full" disabled={busy}>
          Зберегти спостереження
        </button>
      </form>
    </Modal>
  );
}

function Earn({
  providers,
  busy,
  online,
  onSubmit,
}: {
  providers: ProviderState;
  busy: boolean;
  online: boolean;
  onSubmit: (
    j: Omit<Schema["JobCreate"], "idempotency_key">,
  ) => Promise<boolean>;
}) {
  const [role, setRole] = useState(""),
    [location, setLocation] = useState(""),
    [facts, setFacts] = useState(""),
    [job, setJob] = useState(""),
    [provider, setProvider] = useState<"anthropic" | "gemini">("anthropic");
  const enabled =
    providers.metered_inference_enabled &&
    providers.items.some((p) => p.id === provider && p.available);
  return (
    <div className="earn-grid">
      <section className="card">
        <span className="section-label">01 / ЗНАЙТИ НАПРЯМОК</span>
        <h2>Яка робота вам підходить?</h2>
        <p>
          Підготуємо посилання для пошуку. Наразі це не перевірена добірка живих
          вакансій.
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit({
              kind: "income_search",
              provider: "manual",
              payload: { role, location },
            });
          }}
        >
          <Field label="Роль або сфера">
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="Full-stack developer"
              required
              maxLength={200}
            />
          </Field>
          <Field label="Місто або формат">
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Відень / remote"
              maxLength={200}
            />
          </Field>
          <button className="button full" disabled={busy || !online}>
            Підготувати пошук
            <Icon name="arrow" />
          </button>
        </form>
      </section>
      <section className="card">
        <span className="section-label">02 / ПІДГОТУВАТИ ВІДГУК</span>
        <h2>Ваш досвід, ваші факти</h2>
        <p>
          Чернетка лише з наведених вами відомостей. Потрібна перевірка перед
          використанням; нічого не надсилається.
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit({
              kind: "draft_application",
              provider,
              payload: { profile_facts: facts, job_description: job },
            });
          }}
        >
          <Field label="Підтверджені факти вашого профілю">
            <textarea
              value={facts}
              onChange={(e) => setFacts(e.target.value)}
              maxLength={8000}
              required
              placeholder="Досвід, навички, освіта…"
            />
          </Field>
          <Field label="Текст конкретної вакансії">
            <textarea
              value={job}
              onChange={(e) => setJob(e.target.value)}
              maxLength={8000}
              required
              placeholder="Вставте опис із джерела"
            />
          </Field>
          <Field label="Модель для чернетки">
            <select
              value={provider}
              onChange={(e) =>
                setProvider(e.target.value as "anthropic" | "gemini")
              }
            >
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Gemini</option>
            </select>
          </Field>
          {!enabled && (
            <p className="fine">
              Цей провайдер не підключено або платні виклики вимкнені.
              Налаштування виконує власник сервера.
            </p>
          )}
          <button
            className="button full"
            disabled={busy || !online || !enabled}
          >
            Підготувати чернетку
          </button>
        </form>
      </section>
    </div>
  );
}
function JobResult({ result }: { result: Record<string, unknown> }) {
  const links = Array.isArray(result.links)
    ? (result.links as { title: string; url: string }[])
    : [];
  const suggestions = Array.isArray(result.suggestions)
    ? (result.suggestions as string[])
    : [];
  return (
    <div className="job-result">
      {typeof result.summary === "string" && (
        <p className="preserve">{result.summary}</p>
      )}
      {typeof result.monthly_savings_minor === "number" && (
        <p>
          Потенціал: <b>{money(result.monthly_savings_minor)} / місяць</b>.
          Перший місяць: {money(Number(result.first_month_savings_minor))}.
          Сценарій, не отриманий дохід.
        </p>
      )}
      {links.map((link) => (
        <a
          key={link.url}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {link.title}
          <Icon name="arrow" size={16} />
        </a>
      ))}
      {suggestions.length > 0 && (
        <ul>
          {suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
      {result.review_required === true && (
        <span className="pill">Неперевірена чернетка · не надіслано</span>
      )}
    </div>
  );
}
