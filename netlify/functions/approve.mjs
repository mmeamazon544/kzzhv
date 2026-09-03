// Approve endpoint. Links in the proof email land here with a token tied
// to the bulletin's identifier and proof revision. The page confirms with
// one button (a plain GET must stay side-effect free: mail scanners
// prefetch links). The button POST fires a repository_dispatch that the
// publish workflow acts on.
import { dispatch, linkOk, notConfigured, page, secret } from "./common.mjs";

export const config = { path: "/approve" };

export default async function handler(req) {
  if (!secret()) return notConfigured();
  const url = new URL(req.url);
  const id = url.searchParams.get("id") || "";
  const rev = url.searchParams.get("rev") || "";
  const sig = url.searchParams.get("sig") || "";

  if (!linkOk(id, rev, sig)) {
    return page("Approve", "<h1>Approve</h1><p class='note'>This link is not valid — it may belong to an older proof. Use the links in the latest proof email.</p>");
  }

  if (req.method === "POST") {
    const ok = await dispatch("bulletin-approve", { id, rev });
    return page("Approved", ok
      ? `<h1>Approved</h1><p class='ok'>The bulletin for ${id} is approved. It will be published and sent at the appointed hour — or right away if that hour has passed.</p>`
      : "<h1>Approve</h1><p class='note'>Something went wrong reaching the repository; try again in a minute.</p>");
  }

  return page("Approve", `
<h1>Approve</h1>
<p>Approve the bulletin for <strong>${id}</strong>?</p>
<form method="POST"><button type="submit">Approve this bulletin</button></form>
<p class="note">Approving publishes it to the site and sends it to the list at the appointed hour.</p>`);
}
