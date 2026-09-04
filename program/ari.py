"""Superseded by family.py (member "ari"). Kept as a shim."""

import sys

if __name__ == "__main__":
    sys.argv = [sys.argv[0],
                "--proof" if "--proof" in sys.argv else "--live",
                "--member", "ari"] + [a for a in sys.argv[1:] if not a.startswith("--")]
    import family
    # family.py runs from __main__; emulate its entry.
    from datetime import date
    proof = "--proof" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != "ari"]
    sat = date.fromisoformat(args[0]) if args else family.next_saturday()
    family.build_and_send("ari", sat, proof)
