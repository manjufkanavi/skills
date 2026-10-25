# Discovering a practice API's endpoints and auth model

Many learning courses use free "practice" APIs (fake stores, test services) so
learners can hit real HTTP endpoints without paying or exposing production data.
Their true shape is rarely obvious from the landing page — it's usually a React/
SPA whose routes are embedded in the served HTML. Discovering them reliably:

## 1. Enumerate endpoints (SPA case)

The endpoint list is often baked into the page's JS bundle or HTML, not visible
in static markup. Techniques that worked on `restful-api.dev`:

- **curl the page and grep for URLs**, filtering out trackers/CDNs:
  ```bash
  curl -fsSL https://restful-api.dev/ | grep -ioE 'https?://[a-zA-Z0-9./_\-]+' \
    | grep -vE 'github|googletagmanager|fonts|gstatic' | sort -u
  ```
- **Pull method + endpoint + description** from the DOM (each accordion entry has a
  `MuiChip-label` method chip, then an endpoint `<p>` and description `<p>`):
  ```python
  import re, html
  blocks = re.findall(
    r'<span class="MuiChip-label MuiChip-labelMedium css-14vsv3w">(GET|POST|PUT|PATCH|DELETE)</span>.*?'
    r'<p class="MuiTypography-root MuiTypography-body1 css-1rrq4ez">([^<]+)</p>.*?'
    r'<p class="MuiTypography-root MuiTypography-body2 css-14u3b21">(.*?)</p>',
    doc, re.S)
  ```

## 2. Determine the auth model by probing (don't assume, test)

Probe each endpoint *without* a key first; observe what the server actually says.
Verified behaviour on `restful-api.dev`:

- **`GET /objects` is truly public** — returns 200 with a JSON array of
  `{id, name, data}` even with no `x-api-key`. This is the safe beginner starting
  point.
- **`GET /collections`, `GET/POST/{id}`, and every write all require the
  `x-api-key` header.** Without it they return **403** with a body like
  `"API key is missing. To use this API, include your API key in the 'x-api-key'
  header."`

## 3. Learn how a beginner obtains the key (the gotcha)

Some practice APIs gate even their own **`/register` and `/login`** behind the
same `x-api-key` header. That means you cannot obtain a key through the API — it
must be fetched **once, by hand**, from the web dashboard (e.g. `restful-api.dev/dashboard`).

Teach this explicitly:
- Get the key once via the website; never hard-code it.
- Load it from an environment variable: `os.environ.get("RESTFUL_API_KEY")`.
- If unset, print a friendly hint and exit gracefully rather than crashing.

## 4. Note the response shapes you'll teach against

- `/objects` (public): `[{"id": "1", "name": "...", "data": {...|null}}, ...]` —
  note `data` is inconsistent across items (some have price, some color/capacity,
  one has `null`). Model lessons around this real messiness.
- `/collections` (authed): `[{"collectionName": "phones", "objectCount": 12}, ...]`.
- POST returns **201** and usually echoes the created object with its new `id`.
