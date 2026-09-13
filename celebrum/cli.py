"""Celebrum CLI - the terminal brain.

Usage:  celebrum <command> [options]

Commands:
  init [--demo]        create the brain store (optionally seed demo data)
  ingest duet FILE     ingest a consented Duet memory export (JSON)
  ingest web URL       ingest a public web page (consent + SSRF-guarded)
  ingest html FILE     ingest a local HTML knowledge source (matruswara, etc)
  recall QUERY         identity-grounded memory recall
  simulate SCENARIO    run a 'what if' scenario through the Persona Model
  propose              propose guardrail adaptations (tiered by risk)
  approve ID [--by X]  approve a guardrail change
  reject ID            reject a guardrail change
  revert ID            revert a guardrail change (if reversible)
  guardrails           list guardrails
  persona              show the current Persona Model
  truth                show the Truth Index and flagged memories
  validate             run the neural validation harness
  graph [--out FILE]   export the neuron/synapse graphdb as JSON
  tensor               show Personal Tensor Memory info
  audit [-n N]         tail the audit log
  mcp                  run the MCP stdio server (OpenWorker bridge)
  gui [--port PORT]    launch the local dashboard
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .engine import Celebrum, default_home
from .guardrails import GuardrailEngine


def _print(obj, indent=2):
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, ensure_ascii=False, indent=indent, default=str))
    else:
        print(obj)


def _require(engine):
    if engine.graph.stats()["neurons"] == 0:
        print("warning: memory is empty - try 'celebrum init --demo' or 'celebrum ingest'")
    return engine


def cmd_init(args):
    if args.demo:
        import shutil
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        duet = json.load(open(os.path.join(data_dir, "duet_sample.json"), encoding="utf-8"))
        engine = Celebrum(home=args.home)
        engine.ingest_duet(duet, consent=True, source="duet")
        for name in ("satyasandha.html", "oi.html"):
            src = os.path.join(data_dir, "matruswara", name)
            if os.path.exists(src):
                engine.ingest_html(src, consent=True)
        engine.learn()
        print(f"seeded demo brain at {engine.home}")
        print(json.dumps(engine.snapshot(), ensure_ascii=False, indent=2, default=str))
    else:
        engine = Celebrum(home=args.home)
        engine.store.log("user", "init", risk="low", details={"demo": False}, result="ok")
        print(f"init brain at {engine.home}")


def cmd_ingest(args):
    engine = _require(Celebrum(home=args.home))
    if args.kind == "duet":
        duet = json.load(open(args.target, encoding="utf-8"))
        res = engine.ingest_duet(duet, consent=True)
    elif args.kind == "web":
        res = engine.ingest_web(args.target, consent=True)
    elif args.kind == "html":
        res = engine.ingest_html(args.target, consent=True)
    else:
        raise SystemExit(f"unknown ingest kind {args.kind}")
    _print(res)


def cmd_recall(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.recall(args.query, k=args.k, identity=not args.no_identity), indent=2)


def cmd_simulate(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.simulate(args.scenario))


def cmd_persona(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.persona.to_dict())


def cmd_truth(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.truth().index())
    flagged = engine.truth().flagged()
    if flagged:
        print("flagged:")
        _print(flagged, indent=2)


def cmd_propose(args):
    engine = _require(Celebrum(home=args.home))
    proposals = engine.propose()
    if not proposals:
        print("no new proposals: persona and guardrails are aligned.")
        return
    for i, p in enumerate(proposals, 1):
        print(f"[{i}] ({p['tier']}) {p['rule']}")
        print(f"    rationale: {p['rationale']}")
        pid = p.get("id")
        if pid:
            print(f"    id: {pid}")
    print("\nrun 'celebrum guardrails' to see what to approve.")


def cmd_guardrails(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.guardrails.all(), indent=2)


def cmd_decide(args):
    engine = _require(Celebrum(home=args.home))
    if args.action == "approve":
        _print(engine.approve(args.id, by=args.by))
    elif args.action == "reject":
        _print(engine.reject(args.id, by=args.by))
    elif args.action == "revert":
        _print(engine.revert(args.id, by=args.by))


def cmd_validate(args):
    engine = _require(Celebrum(home=args.home))
    report = engine.validate()
    _print(report)
    ok = report["summary"]["status"] == "PASS"
    sys.exit(0 if ok else 2)


def cmd_graph(args):
    engine = _require(Celebrum(home=args.home))
    data = engine.graph.graph_export(cytoscape=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        print(f"graph exported to {args.out}")
    else:
        _print(data)


def cmd_tensor(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.tensor.summary())


def cmd_audit(args):
    engine = _require(Celebrum(home=args.home))
    tail = engine.store.audit_tail(args.n)
    for row in tail:
        print(f"{row['ts']} | {row['actor']:<9} | {row['action']:<22} | {row.get('risk', '') or '':<6} | "
              f"{row['result']} | {row['details']}")


def cmd_gui(args):
    from .gui import run_gui
    run_gui(home=args.home, host=args.host, port=args.port)


def cmd_status(args):
    engine = _require(Celebrum(home=args.home))
    _print(engine.snapshot())


def build_parser():
    p = argparse.ArgumentParser(prog="celebrum", description="Celebrum - local-first artificial brain (CLI+GUI+MCP)",
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("--home", default=default_home(),
                   help="brain home dir (default: ~/.celebrum or $CELEBRUM_HOME)")
    sub = p.add_subparsers(dest="command")

    c = sub.add_parser("init", help="create the brain store")
    c.add_argument("--demo", action="store_true", help="seed demo data (Duet + matruswara sources)")
    c.set_defaults(func=cmd_init)

    c = sub.add_parser("ingest", help="ingest data")
    c.add_argument("kind", choices=["duet", "web", "html"])
    c.add_argument("target", help="json file | url | html file")
    c.set_defaults(func=cmd_ingest)

    c = sub.add_parser("recall", help="recall memories")
    c.add_argument("query")
    c.add_argument("-k", type=int, default=5)
    c.add_argument("--no-identity", action="store_true")
    c.set_defaults(func=cmd_recall)

    c = sub.add_parser("simulate", help="what-if scenario")
    c.add_argument("scenario")
    c.set_defaults(func=cmd_simulate)

    sub.add_parser("persona", help="show Persona Model").set_defaults(func=cmd_persona)
    sub.add_parser("truth", help="Truth Index").set_defaults(func=cmd_truth)
    sub.add_parser("propose", help="propose guardrails").set_defaults(func=cmd_propose)
    sub.add_parser("guardrails", help="list guardrails").set_defaults(func=cmd_guardrails)
    sub.add_parser("validate", help="run validation harness").set_defaults(func=cmd_validate)
    sub.add_parser("tensor", help="PTM info").set_defaults(func=cmd_tensor)
    sub.add_parser("status", help="brain snapshot").set_defaults(func=cmd_status)

    c = sub.add_parser("decide", help="approve/reject/revert a guardrail")
    c.add_argument("action", choices=["approve", "reject", "revert"])
    c.add_argument("id")
    c.add_argument("--by", default="local-user")
    c.set_defaults(func=cmd_decide)

    c = sub.add_parser("graph", help="export graphdb JSON")
    c.add_argument("--out")
    c.set_defaults(func=cmd_graph)

    c = sub.add_parser("audit", help="audit log")
    c.add_argument("-n", type=int, default=20)
    c.set_defaults(func=cmd_audit)

    c = sub.add_parser("gui", help="launch dashboard")
    c.add_argument("--host", default="127.0.0.1")
    c.add_argument("--port", type=int, default=8477)
    c.set_defaults(func=cmd_gui)

    sub.add_parser("mcp", help="run MCP stdio server").set_defaults(func=cmd_mcp)
    return p


def cmd_mcp(args):
    import sys as _sys
    from .mcp import main as mcp_main
    mcp_main(["--home", args.home])
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return getattr(args, "func")(args)


if __name__ == "__main__":
    main()