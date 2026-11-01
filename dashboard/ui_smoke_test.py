"""Headless UI walkthrough of both journeys using Streamlit AppTest against a running test API.

Run: ECOS_API_URL=http://localhost:8011/api/v1 .venv/bin/python -m dashboard.ui_smoke_test
"""

import os
import sys
import uuid

from streamlit.testing.v1 import AppTest

assert "ECOS_API_URL" in os.environ, "Point ECOS_API_URL at a test backend"
failures: list[str] = []


def check(label: str, at: AppTest, extra: bool = True) -> None:
    problems = [e.value for e in at.exception] + [e.value for e in at.error]
    ok = extra and not problems
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f" -> {problems or 'condition false'}"))
    if not ok:
        failures.append(label)


def nav(at: AppTest, view: str) -> AppTest:
    return at.button(key=f"nav_{view}").click().run()


def texts(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [s.value for s in at.success]
    parts += [t.value for t in at.title] + [i.value for i in at.info]
    return "\n".join(str(p) for p in parts)


at = AppTest.from_file("app.py", default_timeout=120)
at.run()
check("login page renders", at, "Welcome to ECOS" in texts(at))

employee = f"UI{uuid.uuid4().hex[:6].upper()}"
at.text_input[0].input(employee)
at.button[0].click().run()
check("new employee lands on profile", at, at.session_state["gt_view"] == "Profile")

at.selectbox[0].select("vegetarian")
at.checkbox[0].check()
at.button(key="FormSubmitter:preferences-Save preferences").click().run()
check("save preferences", at, "Preferences saved" in texts(at))


def metric(at: AppTest, label: str) -> str:
    return next((m.value for m in at.metric if m.label == label), "")


import httpx  # noqa: E402


def live_recs(at: AppTest) -> list[dict]:
    response = httpx.post(f"{os.environ['ECOS_API_URL']}/recommendations", json={"meal_period": "lunch", "limit": 10},
                          headers={"X-User-Id": at.session_state["user_id"]}, trust_env=False)
    return response.json()["items"]


nav(at, "Home")
check("new user wellness score is 20", at, metric(at, "Wellness score") == "20 / 100")
recs = live_recs(at)
check("recommendations follow vegetarian preference", at, recs and all(i["diet"] == "veg" for i in recs))
nav(at, "Profile")
check("profile shows saved preference", at, at.selectbox[0].value == "vegetarian" and at.checkbox[0].value)
at.selectbox[0].select("non_vegetarian")
at.button(key="FormSubmitter:preferences-Save preferences").click().run()
recs = live_recs(at)
check("preference change updates recommendations immediately", at, any(i["diet"] == "non_veg" for i in recs))
nav(at, "Profile")
check("profile shows updated preference", at, at.selectbox[0].value == "non_vegetarian")
at.selectbox[0].select("vegetarian")
at.button(key="FormSubmitter:preferences-Save preferences").click().run()

for view in ("Home", "Menu"):
    nav(at, view)
    check(f"employee {view}", at)

add_buttons = [b for b in at.button if (b.key or "").startswith("rec_") and not b.disabled]
check("recommendations offer dishes", at, bool(add_buttons))
add_buttons[0].click().run()
check("added to cart", at, len(at.session_state["gt_cart"]) == 1)
checkout = next(b for b in at.button if b.label.startswith("Place order"))
checkout.click().run()
check("checkout -> My orders confirmation", at, at.session_state["gt_view"] == "My orders"
      and "Pickup reference" in texts(at))

nav(at, "My wellness")
check("employee wellness", at, "monthly wellness" in texts(at).lower())
score = metric(at, "Monthly wellness score")
check("wellness score rises after order", at, score and int(score.split()[0]) > 20)
nav(at, "Profile")
check("employee profile reload", at)

check("session token kept for the browser cookie", at, len(at.session_state["gt_session"]) > 30)
for mode in ("Plan my day", "Full menu"):
    nav(at, "Menu")
    at.segmented_control(key="gt_menu_mode").set_value(mode).run()
    check(f"menu view: {mode}", at)
at.segmented_control(key="gt_menu_mode").set_value("For you").run()

at.button(key="sign_out").click().run()
check("sign out", at, at.session_state["user_id"] is None)
at.text_input[0].input("MGR001")
at.button[0].click().run()
check("manager login -> Today", at, at.session_state["gt_view"] == "Today")

nav(at, "Live orders")
check("live orders", at)
advance = [b for b in at.button if (b.key or "").startswith("adv_")]
check("employee order visible to manager", at, bool(advance))
advance[0].click().run()
check("advance order status", at, "→ preparing" in texts(at))

for view in ("Inventory", "Menu management", "Executive"):
    nav(at, view)
    check(f"manager {view}", at)

nav(at, "Forecasting")
at.button(key="FormSubmitter:forecast-Run forecast").click().run()
check("run forecast", at, "Expected customers" in str([m.label for m in at.metric]))

nav(at, "Copilot")
prompt = next(b for b in at.button if (b.key or "").startswith("prompt_"))
prompt.click().run()
check("copilot answers", at, len(at.session_state["gt_copilot_history"]) == 1)

nav(at, "Today")
check("manager today after activity", at)

print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
sys.exit(1 if failures else 0)
