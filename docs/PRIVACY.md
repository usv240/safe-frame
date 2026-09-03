# Data handling

Safe Frame is an open pre-check with no accounts, so there is very little to say
here, and what there is should be exact rather than reassuring. Endpoints differ:
one of them stores what you send it, on purpose, and this document says which.

Nothing in this file is a legal notice. It is a description of what the code
does, and every claim in it is checkable in the repository.

## Checking a video on the page

This is `/v1/analyze`, the **Check your own** panel.

| | |
|---|---|
| The file | Never uploaded. It is decoded in your browser by `<video>` and `<canvas>`; the file itself does not leave your machine. |
| Display | Never. The video element is created but never inserted into the document, so a clip you are checking *because you suspect it flashes* is not played back at you. |
| What is sent | Downscaled RGB samples, on a grid whose longest edge is 48 cells, and the frame rate. Nothing else: no filename, no container metadata, no audio. |
| What is stored | **Nothing.** Both modes evaluate the published criteria over inline rows and write no database records. `tests/test_analyze.py` forces the ClickHouse branch on and fails if any write is reintroduced. |
| Identifiers | A random `byo-<hex>` lineage is generated per request so two callers cannot collide. It is not linked to you and is not retained. |
| Logs | An entry is written only when the query fails, recording the endpoint and the exception type. Your samples and your results are never logged. |

This was not true at first. The regression mode originally persisted the
measured pair and then ran the stored anti-join, which meant timings and
transition counts derived from somebody's own video stayed in the database
indefinitely for no benefit. Both modes now evaluate inline and write nothing.

## Submitting measurements through the API

This is `/v1/scan`, and it is different: **it stores what you give it.**

That is the point of the endpoint. It persists the transition rows you send so
the per-pair anti-join can read them back, under the asset identifiers you
choose. Consequences worth knowing:

- Rows you submit stay in the `violations` table. There is no TTL on it and no
  deletion endpoint.
- Anyone who knows your asset identifiers can read the verdict for that pair.
  Use identifiers that are meaningless outside your own systems if that matters
  to you.
- Identifiers belonging to the published catalogue and to the documented judge
  sample are refused as write targets, so no caller can alter what another sees.
- `/v1/samples` mints a fresh lineage per request for the same reason.

If you do not want measurements retained, use `/v1/analyze`, which answers the
same question and stores nothing.

## API keys

Keys are optional. Every endpoint works without one, at the limits the service
has always had, and a key only raises the per-minute cap on the endpoints that
spend model tokens or write.

- **No account is created.** `POST /v1/keys` asks for nothing: no email, no
  name, no approval step. There is no profile because there is no user record.
- **The key is not stored.** It is an identifier and an issue date signed with an
  HMAC held in Secret Manager. Verifying it is a signature check, not a lookup,
  so there is no credential table to leak.
- **It is shown once**, in the response, and never again. We cannot recover it
  for you because we never had it.
- **It cannot be revoked individually** without rotating the signing secret.
  This is stated on the key itself. Keys stop working 90 days after issue, which
  bounds the exposure of a leaked one. Mint a separate key per integration.
- **What it identifies.** A key id appears in the service logs against calls
  that use it, so a run can be traced afterwards. Nothing else is attached to it.

## The catalogue itself

The 424 titles and their measurements are self-authored synthetic data. No
filmed footage is involved, nothing in it is anyone's personal data, and nothing
on the site plays or renders flashing imagery.

## Third parties

The service runs on Google Cloud Run, reaches Gemini through Vertex AI, and
queries a self-hosted ClickHouse cluster over HTTPS. Gemini receives only
evidence retrieved from the database by tool calls: it is never given your
submitted frames, and it never decides a verdict. Google's own operational logs
are outside our control and are covered by Google Cloud's terms.

## Contact

The repository is the contact point. Open an issue if something here does not
match what the code does, and it will be treated as a defect.
