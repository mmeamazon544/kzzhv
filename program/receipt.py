"""KKZZ contribution receipt generator. Runs on Marc's Mac, by hand, per
contribution — deliberately: donor names and addresses are personal data
and never pass through the public repository or its workflows.

Writes a print-ready HTML receipt (white ground, the crest, the
congregation's 501(c)(3) language, the designated purpose) into
14-TECHNICAL/CLAUDE STUFF/KKZZ RECEIPTS/ and opens it; print to PDF from
the browser and send it to the contributor.

The EIN line prints a placeholder until Marc supplies the number; official
receipts customarily carry it.

Usage:
  python3 program/receipt.py --name "Jane Doe" --amount 250 \
      --designated "the restoration of the original 1904 murals and floors" \
      [--memory "NAME"] [--honor "NAME"] [--date 2026-09-06] [--txn PAYPAL-ID]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

OUT = Path("/Volumes/DB PRIMARY LOCAL/Dropbox/14-TECHNICAL/CLAUDE STUFF/KKZZ RECEIPTS")
CREST = "https://kzzhv.org/assets/images/logo-deer-blush.png"
EIN = "[EIN to be supplied]"


def arg(flag: str, default: str = "") -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main() -> None:
    name = arg("--name")
    amount = float(arg("--amount", "0"))
    designated = arg("--designated", "the general support of the Kehillah")
    memory = arg("--memory")
    honor = arg("--honor")
    when = arg("--date", date.today().isoformat())
    txn = arg("--txn")
    if not name or amount <= 0:
        sys.exit("required: --name and --amount")

    dedication = ""
    if memory:
        dedication = f" in memory of {memory},"
    elif honor:
        dedication = f" in honor of {honor},"

    body = (f"Thank you for your contribution of ${amount:,.2f} to Kehillah "
            f"Kedoshah Zikhron Zvi,{dedication} designated for {designated}.")

    txn_line = (f'<p class="meta">PayPal transaction reference: {txn}</p>' if txn else "")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>KKZZ Contribution Receipt — {name} — {when}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a;
         background: #ffffff; margin: 0; }}
  .sheet {{ max-width: 40rem; margin: 0 auto; padding: 3rem 2.5rem; }}
  .head {{ text-align: center; border-bottom: 2px solid #856a2e; padding-bottom: 1.4rem; }}
  .head img {{ width: 64px; }}
  .head h1 {{ font-size: 1.05rem; letter-spacing: 0.18em; text-transform: uppercase;
             font-weight: 400; margin: 0.8rem 0 0.2rem; }}
  .head .sub {{ font-size: 0.72rem; letter-spacing: 0.3em; text-transform: uppercase;
               color: #856a2e; }}
  h2 {{ font-size: 0.85rem; letter-spacing: 0.22em; text-transform: uppercase;
       font-weight: 400; color: #856a2e; margin: 2.2rem 0 1rem; text-align: center; }}
  p {{ font-size: 1.02rem; line-height: 1.65; }}
  .meta {{ font-size: 0.85rem; color: #666; }}
  .legal {{ font-size: 0.85rem; color: #444; border-top: 1px solid #ccc;
           padding-top: 1rem; margin-top: 2.2rem; }}
  .date {{ text-align: right; font-size: 0.9rem; color: #444; }}
</style></head><body>
<div class="sheet">
  <div class="head">
    <img src="{CREST}" alt="">
    <h1>Kehillah Kedoshah Zikhron Zvi</h1>
    <div class="sub">Hudson Valley &nbsp;&middot;&nbsp; kzzhv.org</div>
  </div>
  <h2>Receipt of Charitable Contribution</h2>
  <p class="date">{when}</p>
  <p>Dear {name},</p>
  <p>{body}</p>
  <p>No goods or services were provided in exchange for this contribution.</p>
  {txn_line}
  <p>With the gratitude of the Congregation,</p>
  <p>Kehillah Kedoshah Zikhron Zvi</p>
  <p class="legal">Kehillah Kedoshah Zikhron Zvi is a nonprofit organization
  recognized as tax-exempt under Section 501(c)(3) of the Internal Revenue
  Code; contributions are tax-deductible to the extent permitted by law.
  EIN: {EIN}. Correspondence: kehillatzikhronzvi@gmail.com.</p>
</div>
</body></html>"""

    OUT.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in name if c.isalnum() or c in " -").strip() or "Contributor"
    out = OUT / f"KKZZ Receipt {when} {safe}.html"
    out.write_text(html)
    print(out)
    subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
