// Request-changes endpoint. A plain page with one text box; submitting
// fires a repository_dispatch that regenerates the bulletin with the
// instructions and sends a fresh proof.
import { dispatch, linkOk, notConfigured, page, secret } from "./common.mjs";

export const config = { path: "/changes" };

export default async function handler(req) {
  if (!secret()) return notConfigured();
  const url = new URL(req.url);
  const id = url.searchParams.get("id") || "";
  const rev = url.searchParams.get("rev") || "";
  const sig = url.searchParams.get("sig") || "";

  if (!linkOk(id, rev, sig)) {
    return page("Request changes", "<h1>Request Changes</h1><p class='note'>This link is not valid — it may belong to an older proof. Use the links in the latest proof email.</p>");
  }

  if (req.method === "POST") {
    const form = await req.formData();
    const instructions = String(form.get("instructions") || "").trim();
    if (!instructions) {
      return page("Request changes", "<h1>Request Changes</h1><p class='note'>Write what should change, then submit.</p>");
    }
    const ok = await dispatch("bulletin-changes", { id, rev, instructions });
    return page("Request changes", ok
      ? "<h1>Request Changes</h1><p class='ok'>Understood. A fresh proof is being prepared and will arrive shortly.</p>"
      : "<h1>Request Changes</h1><p class='note'>Something went wrong reaching the repository; try again in a minute.</p>");
  }

  return page("Request changes", `
<h1>Request Changes</h1>
<p>Bulletin for <strong>${id}</strong>. Say what should change, in plain English.</p>
<form method="POST">
  <textarea name="instructions" autofocus placeholder="e.g. Move the memorial notice above the class listing; cite the Zohar passage instead of the midrash."></textarea>
  <button type="submit">Send and regenerate</button>
</form>`);
}
