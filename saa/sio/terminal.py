"""Swan Interaction Overlay — Interactive Terminal Interface.

A text-based interface for conversing with and observing a Swan agent.
Run: python -m saa.sio.terminal
"""

from __future__ import annotations

import sys

from saa.sio.core.session import SessionManager
from saa.sio.core.schemas import SessionConfig


COMMANDS = {
    "/state":     "Show full internal state",
    "/mods":      "Show neuromodulators",
    "/rels":      "Show relationships",
    "/values":    "Show valuation map",
    "/rationale": "Show last action rationale",
    "/memory":    "Show memory summary",
    "/history":   "Show conversation history",
    "/inject":    "Inject event: /inject <type> [key=val ...]",
    "/save":      "Save session checkpoint",
    "/mode":      "Toggle view mode: /mode human|analyst|engineer",
    "/help":      "Show this help",
    "/quit":      "Exit",
}


def bar(value: float, width: int = 20, inverted: bool = False) -> str:
    pct = max(0.0, min(1.0, value))
    filled = int(pct * width)
    if inverted:
        color = "\033[31m" if pct > 0.6 else "\033[33m" if pct > 0.3 else "\033[32m"
    else:
        color = "\033[31m" if pct < 0.3 else "\033[33m" if pct < 0.6 else "\033[32m"
    reset = "\033[0m"
    return f"{color}{'█' * filled}{'░' * (width - filled)}{reset} {value:.3f}"


def dim(text: str) -> str:
    return f"\033[90m{text}\033[0m"


def cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"


def yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def red(text: str) -> str:
    return f"\033[31m{text}\033[0m"


def green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


class TerminalUI:
    def __init__(self) -> None:
        self.mgr = SessionManager(storage_dir="/tmp/sio_sessions")
        self.session_id: str = ""
        self.mode = "analyst"

    def start(self) -> None:
        print()
        print(cyan("╔══════════════════════════════════════════════════════════╗"))
        print(cyan("║") + "    Swan Interaction Overlay — Terminal Interface         " + cyan("║"))
        print(cyan("║") + dim("    A window into the Swan system, not the system itself ") + cyan("║"))
        print(cyan("╚══════════════════════════════════════════════════════════╝"))
        print()

        config = SessionConfig(view_mode=self.mode)
        self.session_id = self.mgr.create_session(config)
        print(dim(f"  Session: {self.session_id}"))
        print(dim(f"  Mode: {self.mode} (change with /mode)"))
        print(dim(f"  Type /help for commands"))
        print()

        while True:
            try:
                user_input = input(f"{green('You')} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    break
                continue

            self._handle_chat(user_input)

    def _handle_chat(self, text: str) -> None:
        turn = self.mgr.process_input(self.session_id, text)

        # Response
        print()
        print(f"{cyan('Swan')} > {turn.response_text}")
        print()

        # Action info (analyst + engineer)
        if self.mode != "human":
            ai = turn.action_intent
            print(dim(f"  action: {ai.action_type} (score: {ai.score:.3f}, conflict: {ai.conflict})"))

            # State diffs
            if turn.state_diffs:
                diffs = [f"{d.field}:{d.delta:+.4f}" for d in turn.state_diffs if d.delta]
                if diffs:
                    print(dim(f"  changes: {', '.join(diffs[:6])}"))

            # Key metrics
            s = turn.state_after
            mods = s.modulators
            print(dim(f"  energy:{s.energy:.3f} stress:{mods.get('stress_load',0):.3f} "
                      f"cont:{s.continuity_score:.3f} viab:{s.viability:.3f}"))

        # Competing actions (engineer)
        if self.mode == "engineer" and turn.action_intent.competing_actions:
            top = turn.action_intent.competing_actions[:3]
            alts = ", ".join(f"{c.get('action','?')}:{c.get('score',0):.3f}" for c in top)
            print(dim(f"  alternatives: {alts}"))
            if turn.action_intent.rationale:
                for r in turn.action_intent.rationale[:2]:
                    print(dim(f"  rationale: {r}"))

        print()

    def _handle_command(self, cmd: str) -> bool:
        """Returns False to exit."""
        parts = cmd.split()
        command = parts[0].lower()

        if command == "/quit":
            print("Goodbye.")
            return False

        elif command == "/help":
            print()
            for c, desc in COMMANDS.items():
                print(f"  {cyan(c):30s} {desc}")
            print()

        elif command == "/state":
            self._show_state()

        elif command == "/mods":
            self._show_modulators()

        elif command == "/rels":
            self._show_relationships()

        elif command == "/values":
            self._show_values()

        elif command == "/rationale":
            self._show_rationale()

        elif command == "/memory":
            self._show_memory()

        elif command == "/history":
            self._show_history()

        elif command == "/save":
            tick = self.mgr.create_checkpoint(self.session_id)
            print(f"  Checkpoint saved at tick {tick}")
            print()

        elif command == "/mode":
            if len(parts) > 1 and parts[1] in ("human", "analyst", "engineer"):
                self.mode = parts[1]
                print(f"  Mode set to: {self.mode}")
            else:
                print(f"  Current mode: {self.mode}")
                print(f"  Usage: /mode human|analyst|engineer")
            print()

        elif command == "/inject":
            if len(parts) < 2:
                print("  Usage: /inject <event_type> [key=val ...]")
                print("  Events: damage, betrayal, stabilizing_presence, resource_shock,")
                print("          hazard_spike, trust_gain, agent_removal")
            else:
                event_type = parts[1]
                data = {}
                for p in parts[2:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        try:
                            data[k] = float(v)
                        except ValueError:
                            data[k] = v
                snapshot = self.mgr.inject_event(self.session_id, event_type, data)
                print(f"  {yellow('Event injected:')} {event_type}")
                print(dim(f"  energy:{snapshot.energy:.3f} stress:{snapshot.modulators.get('stress_load',0):.3f} "
                          f"cont:{snapshot.continuity_score:.3f}"))
            print()

        else:
            print(f"  Unknown command: {command}. Type /help for options.")
            print()

        return True

    def _show_state(self) -> None:
        s = self.mgr.get_state(self.session_id)
        if not s:
            print("  No state available.")
            return
        print()
        print(cyan("  ── Internal State ──"))
        print(f"  Energy:        {bar(s.energy)}")
        print(f"  Viability:     {bar(s.viability)}")
        print(f"  Continuity:    {bar(s.continuity_score)}")
        print(f"  Mem Integrity: {bar(s.memory_integrity)}")
        print(f"  Damage:        {bar(s.damage, inverted=True)}")
        print(f"  Strain:        {bar(s.strain, inverted=True)}")
        print(f"  Temperature:   {bar(s.temperature)}")
        print()

    def _show_modulators(self) -> None:
        s = self.mgr.get_state(self.session_id)
        if not s:
            return
        print()
        print(cyan("  ── Neuromodulators ──"))
        for k, v in s.modulators.items():
            print(f"  {k:22s} {bar(v)}")
        print()

    def _show_relationships(self) -> None:
        bundle = self.mgr._sessions.get(self.session_id)
        if not bundle:
            return
        rels = bundle[1].get_relationship_graph()
        print()
        print(cyan("  ── Relationships ──"))
        if not rels:
            print("  No relationships yet.")
        for agent_id, rel in rels.items():
            trust = rel.get("trust", 0)
            bond = rel.get("bond_strength", 0)
            attach = rel.get("attachment", 0)
            betrayals = rel.get("betrayal_count", 0)
            trust_color = green if trust > 0.5 else yellow if trust > 0.3 else red
            print(f"  {agent_id:15s} trust:{trust_color(f'{trust:.3f}')} bond:{bond:.3f} "
                  f"attach:{attach:.3f} betrayals:{betrayals}")
        print()

    def _show_values(self) -> None:
        s = self.mgr.get_state(self.session_id)
        if not s:
            return
        print()
        print(cyan("  ── Values ──"))
        for k, v in sorted(s.values.items(), key=lambda x: -x[1]):
            print(f"  {k:22s} {bar(v)}")
        print()

    def _show_rationale(self) -> None:
        bundle = self.mgr._sessions.get(self.session_id)
        if not bundle:
            return
        rat = bundle[1].get_rationale_trace()
        print()
        print(cyan("  ── Last Action Rationale ──"))
        print(f"  Selected: {rat.get('selected', '?')} (score: {rat.get('selected_score', 0):.3f})")
        cands = rat.get("candidates", [])
        for c in cands[:5]:
            print(f"    {c.get('action','?'):12s} {c.get('score',0):.3f}")
        conflict = rat.get("conflict")
        if conflict:
            print(f"  {yellow('Conflict:')} {conflict.get('rationale', '')}")
        print()

    def _show_memory(self) -> None:
        bundle = self.mgr._sessions.get(self.session_id)
        if not bundle:
            return
        mem = bundle[1].get_memory_snapshot()
        print()
        print(cyan("  ── Memory ──"))
        print(f"  Episodic:    {mem.get('episodic_count', 0)}")
        print(f"  Semantic:    {mem.get('semantic_count', 0)}")
        print(f"  Relational:  {mem.get('relational_count', 0)}")
        print(f"  Last tick:   {mem.get('last_encoded_tick', 0)}")
        print()

    def _show_history(self) -> None:
        history = self.mgr.get_history(self.session_id)
        print()
        print(cyan("  ── Conversation History ──"))
        for t in history:
            ai = t.action_intent
            s = t.state_after
            print(f"  {dim(f'[{t.tick}]')} {green('You')}: {t.user_input[:50]}")
            stress = s.modulators.get("stress_load", 0)
            meta = f"({ai.action_type} e:{s.energy:.2f} s:{stress:.2f})"
            print(f"       {cyan('Swan')}: {t.response_text[:50]}  {dim(meta)}")
        print()


def main() -> None:
    ui = TerminalUI()
    ui.start()


if __name__ == "__main__":
    main()
