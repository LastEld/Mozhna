import { test, expect, type Page } from "@playwright/test";

const password = "synthetic-e2e-password";
async function navigate(page: Page, name: string) {
  await page
    .locator("nav button:visible")
    .filter({ hasText: new RegExp(name, "i") })
    .click();
}
test.beforeEach(async ({ request }) => {
  const login = await request.post("/api/v1/auth/login", {
    data: { password },
  });
  expect(login.ok()).toBeTruthy();
  const auth = await login.json();
  const erased = await request.delete("/api/v1/data", {
    headers: { "X-CSRF-Token": auth.csrf_token },
    data: { confirmation: "DELETE" },
  });
  expect(erased.ok()).toBeTruthy();
});

test.afterEach(async ({ context }, info) => {
  if (info.status === info.expectedStatus) return;
  for (const current of context.pages()) {
    console.log(
      "Failure page:",
      await current
        .locator("body")
        .innerText({ timeout: 1000 })
        .catch(() => "unavailable"),
    );
  }
});

test("money, plan, observation, durable job, CSV and reconnect", async ({
  page,
  context,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Увійти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Зараз", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Оновити кошти", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Заповнити приклад", exact: true })
    .click();
  await page.getByRole("checkbox", { name: /Я звірив/ }).check();
  await page
    .getByRole("button", { name: "Зберегти кошти", exact: true })
    .click();
  await expect(page.locator("dialog")).toHaveCount(0);
  await expect(page.locator(".balance-value")).toContainText("50,00");
  await page
    .getByRole("button", { name: "Перевірити покупку", exact: true })
    .click();
  await page.getByLabel("Вартість покупки, €").fill("70");
  await page.getByRole("button", { name: "Перевірити", exact: true }).click();
  await expect(page.locator("dialog")).toContainText("Можна, але…");
  await page.getByRole("button", { name: "Закрити", exact: true }).click();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBeFalsy();
  await page.screenshot({
    path: info.outputPath("money-dashboard.png"),
    fullPage: true,
  });

  await navigate(page, "Мої плани");
  await page
    .getByRole("button", { name: "Створити перший план", exact: true })
    .click();
  await page.getByLabel("Назва", { exact: true }).fill("Сік на роботу");
  await page.getByLabel("Що важливо зберегти").fill("200 мл, той самий смак");
  await page.getByLabel("Звична ціна за випадок, €").fill("1,50");
  await page.getByLabel("Альтернатива за той самий обсяг, €").fill("0,50");
  await page
    .getByRole("button", { name: "Зберегти пропозицію", exact: true })
    .click();
  await page.getByRole("button", { name: "Спробувати", exact: true }).click();
  await expect(page.locator(".plan-card")).toContainText("Активний");
  await page
    .getByRole("button", { name: "Записати результат", exact: true })
    .click();
  await page.getByLabel("Фактично витрачено, €").fill("0,50");
  await page
    .getByRole("button", { name: "Зберегти спостереження", exact: true })
    .click();
  await expect(page.locator(".observed")).toContainText("1,00");
  await page
    .getByRole("button", { name: "Перераховувати щодня", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Щоденний розрахунок увімкнено" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Порахувати у фоні", exact: true })
    .click();
  // A second page reads the persisted result after the initiating page closes.
  const resumed = await context.newPage();
  resumed.on("pageerror", (e) => errors.push(e.message));
  await page.close();
  await resumed.goto("/");
  await navigate(resumed, "Простір");
  await expect(resumed.locator(".job-row").first()).toContainText("Готово", {
    timeout: 15_000,
  });
  await expect(resumed.locator(".job-row").first()).toContainText("20,00");
  await resumed.screenshot({
    path: info.outputPath("cloud-jobs.png"),
    fullPage: true,
  });

  await navigate(resumed, "Рух");
  await resumed.getByRole("button", { name: /Імпорт CSV/ }).click();
  await resumed
    .getByLabel("Або вставте CSV", { exact: true })
    .fill(
      "date,description,amount_minor,external_id\n2026-09-08,Сік,-150,qa-1",
    );
  await resumed
    .getByRole("button", { name: "Імпортувати записи", exact: true })
    .click();
  await expect(resumed.locator("tbody tr")).toHaveCount(1);
  await resumed.getByRole("button", { name: /Імпорт CSV/ }).click();
  await resumed
    .getByLabel("Або вставте CSV", { exact: true })
    .fill(
      "date,description,amount_minor,external_id\n2026-09-08,Сік,-150,qa-1",
    );
  await resumed
    .getByRole("button", { name: "Імпортувати записи", exact: true })
    .click();
  await expect(resumed.locator("dialog")).toHaveCount(0);
  await expect(resumed.locator("tbody tr")).toHaveCount(1);
  await context.setOffline(true);
  await expect(
    resumed.getByRole("status").filter({ hasText: "Немає з’єднання" }),
  ).toBeVisible();
  await expect(
    resumed.getByRole("button", { name: /Імпорт CSV/ }),
  ).toBeDisabled();
  await context.setOffline(false);
  await expect(
    resumed.getByRole("status").filter({ hasText: "Немає з’єднання" }),
  ).toHaveCount(0);
  await navigate(resumed, "Зараз");
  await expect(resumed.locator(".balance-value")).toContainText("50,00");
  expect(errors).toEqual([]);
});

test("an open money form cannot overwrite a newer snapshot", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Увійти", exact: true }).click();
  await page
    .getByRole("button", { name: "Оновити кошти", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Заповнити приклад", exact: true })
    .click();
  await page.getByRole("checkbox", { name: /Я звірив/ }).check();
  const auth = await (await page.request.get("/api/v1/auth/me")).json();
  const competing = await page.request.put("/api/v1/snapshot", {
    headers: { "X-CSRF-Token": auth.csrf_token },
    data: {
      expected_version: 0,
      snapshot: {
        balance_minor: 200000,
        reserve_minor: 0,
        goal_minor: 0,
        living_budget_minor: 0,
        commitments: [],
        incomes: [],
        as_of: new Date().toISOString(),
        currency: "EUR",
        horizon_days: 30,
      },
    },
  });
  expect(competing.ok()).toBeTruthy();
  // Focus refresh updates parent state while preserving the user's open draft.
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.locator(".balance-value")).toContainText("2");
  await page
    .getByRole("button", { name: "Зберегти кошти", exact: true })
    .click();
  await expect(page.locator('dialog [role="alert"]')).toBeVisible();
  const saved = await (await page.request.get("/api/v1/snapshot")).json();
  expect(saved.snapshot.balance_minor).toBe(200000);
});

test("public offline reload [WEBKIT-OFFLINE-01]", async ({
  page: initial,
  context,
  browserName,
}) => {
  await initial.goto("/");
  await initial.evaluate(() => navigator.serviceWorker.ready.then(() => undefined));
  const page = await context.newPage();
  await initial.close();
  await page.goto("/");
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Увійти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Зараз", exact: true }),
  ).toBeVisible();
  await page.evaluate(() =>
    navigator.serviceWorker.ready.then(() => undefined),
  );
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
    )
    .toBeTruthy();
  const cachedPaths = await page.evaluate(async () => {
    const keys = await caches.keys();
    const requests = await Promise.all(
      keys.map(async (key) => (await caches.open(key)).keys()),
    );
    return requests.flat().map((request) => new URL(request.url).pathname);
  });
  expect(cachedPaths).toEqual(["/offline.html"]);
  await context.setOffline(true);
  await expect(
    page.getByRole("status").filter({ hasText: "Немає з’єднання" }),
  ).toBeVisible();
  // This remains an executed, expected failure, NOT evidence that iPhone offline works.
  // An unexpected pass fails CI and requires removing this annotation after review.
  // Reproduced with both Page.reload and location.reload; see docs/CLIENTS.md.
  test.fail(
    browserName === "webkit",
    "WEBKIT-OFFLINE-01: offline SW navigation remains unresolved in WebKit automation; https://playwright.dev/docs/service-workers",
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Зараз немає з’єднання" }),
  ).toBeVisible();
  await expect(page.locator(".balance-value")).toHaveCount(0);
  await context.setOffline(false);
  await page.getByRole("link", { name: "Спробувати знову" }).click();
  await expect(
    page.getByRole("heading", { name: "Зараз", exact: true }),
  ).toBeVisible();
});
