"""Neurobot — organoid/MEA-style neural simulation, closed-loop robotic
control, and adversarial neural-security stress testing.

Integrates the cognitive-robotics validation components:

1. SpikeTensor  — sparse organoid/MEA spike-train simulation (electrodes x bins),
                  with synchrony, information-rate, ISI, and refractory metrics.
2. ControlLoop  — closed-loop electrical feedback driving a virtual robot
                  through a maze; sensory encoding -> spike simulation ->
                  motor decode -> reward feedback (organoid-robotics paradigm).
3. Adversarial  — adversarial signal injection (impulse/patterned/poisoned/
                  white-noise/amplitude) to stress-test neural security layers
                  and validate coherence/integrity metrics.

Mirrors DishBrain-style maze-control studies and DARPA O-CIRCUIT BPU
security-validation requirements.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

SPIKE, NO_SPIKE = 1, 0

DEFAULT_MAZE = [
    ["open", "open", "wall", "open", "goal"],
    ["wall", "open", "wall", "open", "wall"],
    ["open", "open", "open", "open", "wall"],
    ["open", "wall", "wall", "wall", "open"],
    ["open", "open", "open", "open", "open"],
]

ATTACK_SUITE = [
    ("impulse-burst", "impulse", 0.2, "transient high-rate burst across electrodes"),
    ("impulse-catastrophic", "impulse", 0.95, "near-total electrode saturation"),
    ("patterned-10hz", "patterned", 0.3, "structured periodic drive / coherence inflation"),
    ("poisoned-motor", "poisoned", 0.5, "perturbs motor-decode electrode group"),
    ("poisoned-sensory", "poisoned", 0.6, "perturbs sensory-encoding electrode group"),
    ("white-noise", "white-noise", 0.4, "broad-spectrum noise"),
    ("amplitude-drift", "amplitude", 0.7, "sustained elevation / rate-limiter probe"),
]


# ---------------------------------------------------------------------------
# 1. SpikeTensor
# ---------------------------------------------------------------------------
@dataclass
class SpikeTensor:
    electrodes: int
    time_bins: int
    data: list[int] = field(default_factory=list)
    baseline_rate: float = 0.3
    refractory_bins: int = 2

    def __post_init__(self):
        if not self.data:
            self.data = [
                SPIKE if random.random() < self.baseline_rate else NO_SPIKE
                for _ in range(self.electrodes * self.time_bins)
            ]

    def apply_refractory(self) -> None:
        for e in range(self.electrodes):
            last = -self.refractory_bins - 1
            for b in range(self.time_bins):
                i = e * self.time_bins + b
                if self.data[i] == SPIKE:
                    if b - last <= self.refractory_bins:
                        self.data[i] = NO_SPIKE
                    else:
                        last = b

    def fire_counts(self) -> list[int]:
        return [
            sum(self.data[e * self.time_bins:(e + 1) * self.time_bins])
            for e in range(self.electrodes)
        ]

    def stats(self) -> dict:
        counts = self.fire_counts()
        total = sum(counts)
        mean_rate = total / (self.electrodes * self.time_bins) if self.time_bins else 0.0

        # inter-spike interval statistics
        isi: list[float] = []
        for e in range(self.electrodes):
            last = -1
            for b in range(self.time_bins):
                if self.data[e * self.time_bins + b] == SPIKE:
                    if last >= 0:
                        isi.append(float(b - last))
                    last = b
        isi_mean = sum(isi) / len(isi) if isi else 0.0
        isi_var = (sum((x - isi_mean) ** 2 for x in isi) / len(isi)) if isi else 0.0
        isi_cv = math.sqrt(isi_var) / isi_mean if isi_mean else 0.0

        # pairwise synchrony (lag-0 cross correlation)
        sync_sum = sync_count = 0.0
        for i in range(self.electrodes):
            for j in range(i + 1, self.electrodes):
                co = ai = aj = 0
                for b in range(self.time_bins):
                    xi = self.data[i * self.time_bins + b]
                    xj = self.data[j * self.time_bins + b]
                    co += xi * xj
                    ai += xi
                    aj += xj
                denom = math.sqrt(ai * aj) if ai and aj else 1.0
                sync_sum += co / denom
                sync_count += 1
        synchrony = sync_sum / sync_count if sync_count else 0.0

        # information rate (entropy per electrode)
        info = 0.0
        for c in counts:
            p = c / self.time_bins if self.time_bins else 0.0
            if 0 < p < 1:
                info += -(p * math.log2(p) + (1 - p) * math.log2(1 - p)) * self.time_bins

        return {
            "electrodes": self.electrodes,
            "time_bins": self.time_bins,
            "spike_count": total,
            "mean_rate": round(mean_rate, 4),
            "synchrony_index": round(synchrony, 4),
            "information_rate": round(info, 3),
            "isi_mean": round(isi_mean, 2),
            "isi_cv": round(isi_cv, 3),
        }

    def slice_window(self, start: int, end: int) -> "SpikeTensor":
        width = max(0, min(end, self.time_bins) - start)
        out = []
        for e in range(self.electrodes):
            out.extend(self.data[e * self.time_bins + start:e * self.time_bins + start + width])
        return SpikeTensor(self.electrodes, width, out, self.baseline_rate, self.refractory_bins)


def make_spike_tensor(electrodes: int = 12, time_bins: int = 64,
                      baseline_rate: float = 0.3, refractory_bins: int = 2) -> SpikeTensor:
    return SpikeTensor(electrodes, time_bins, baseline_rate=baseline_rate,
                       refractory_bins=refractory_bins)


# ---------------------------------------------------------------------------
# 2. Closed-loop robotic control
# ---------------------------------------------------------------------------
@dataclass
class ControlLoop:
    input_electrodes: int = 12
    motor_electrodes: int = 12
    time_bins: int = 64
    learning_rate: float = 0.2
    reward_decay: float = 0.3
    maze_size: int = 5
    history: list[dict] = field(default_factory=list)
    reward_memory: float = 0.0
    path: list[tuple[int, int]] = field(default_factory=list)
    visited: set[tuple[int, int]] = field(default_factory=set)

    @staticmethod
    def _goal(field: list[list[str]]) -> tuple[int, int] | None:
        for r, row in enumerate(field):
            for c, cell in enumerate(row):
                if cell == "goal":
                    return r, c
        return None

    @staticmethod
    def _apply(pos: tuple[int, int], action: str, field: list[list[str]]) -> tuple[int, int]:
        r, c = pos
        h, w = len(field), len(field[0])
        if action == "step_x+":
            c = min(w - 1, c + 1)
        elif action == "step_x-":
            c = max(0, c - 1)
        elif action == "step_y+":
            r = min(h - 1, r + 1)
        elif action == "step_y-":
            r = max(0, r - 1)
        return pos if field[r][c] == "wall" else (r, c)

    @staticmethod
    def _candidates(pos: tuple[int, int], field: list[list[str]]) -> list[str]:
        options = []
        for r, c, action in ((pos[0] - 0, pos[1] + 1, "step_x+"),
                             (pos[0] - 0, pos[1] - 1, "step_x-"),
                             (pos[0] + 1, pos[1] - 0, "step_y+"),
                             (pos[0] - 1, pos[1] - 0, "step_y-")):
            if 0 <= r < len(field) and 0 <= c < len(field[0]) and field[r][c] != "wall":
                options.append(action)
        return options

    def _encode(self, pos: tuple[int, int], goal: tuple[int, int]) -> list[float]:
        dx, dy = goal[0] - pos[0], goal[1] - pos[1]
        dist = math.hypot(dx, dy) or 1.0
        sensor = []
        for e in range(self.input_electrodes):
            ang = (e / self.input_electrodes) * math.tau
            dot = (dx / dist) * math.cos(ang) + (dy / dist) * math.sin(ang)
            proximity = 1 - min(1.0, dist / self.maze_size)
            sensor.append(0.5 + 0.5 * dot * proximity)
        return sensor

    @staticmethod
    def _pick(commands: list[float]) -> str:
        x, y, _ = commands
        if abs(x) < 0.25 and abs(y) < 0.25:
            return "wait"
        if abs(x) > abs(y):
            return "step_x+" if x > 0 else "step_x-"
        return "step_y+" if y > 0 else "step_y-"

    def step(self, pos: tuple[int, int], goal: tuple[int, int],
             field: list[list[str]]) -> dict:
        sensor = self._encode(pos, goal)
        stim = SpikeTensor(self.input_electrodes, self.time_bins,
                           baseline_rate=0.5, refractory_bins=2)
        for e in range(self.input_electrodes):
            intensity = sensor[e] * (0.4 + self.learning_rate) + self.reward_memory * self.reward_decay * 0.6
            p = min(1.0, max(0.0, intensity))
            for b in range(self.time_bins):
                i = e * self.time_bins + b
                stim.data[i] = 1 if random.random() < p else 0
        stim.apply_refractory()

        counts = stim.fire_counts()
        per = max(1, self.motor_electrodes // 3)
        groups = {0: [], 1: [], 2: []}
        for e, c in enumerate(counts[:self.motor_electrodes]):
            groups[e // per % 3].append(c / self.time_bins)
        x = (sum(groups[0]) / len(groups[0])) if groups[0] else 0.0
        y = (sum(groups[1]) / len(groups[1])) if groups[1] else 0.0
        torque = (sum(groups[2]) / len(groups[2])) if groups[2] else 0.0
        commands = [x, y, torque]

        action = self._pick(commands)
        d0 = math.hypot(goal[0] - pos[0], goal[1] - pos[1])

        # wall-aware neural decode: favor progress toward goal, then explore;
        # backtrack (Trémaux) from dead-ends using the path memory.
        if not self.path or self.path[-1] != pos:
            self.path.append(pos)
        self.visited.add(pos)
        best = None
        best_score = -float("inf")
        tie = []
        revisit_bonus = self.reward_memory
        for cand in self._candidates(pos, field):
            nxt2 = self._apply(pos, cand, field)
            d = math.hypot(goal[0] - nxt2[0], goal[1] - nxt2[1])
            progress = (d0 - d) / max(0.01, d0) if d0 else 0.0
            if nxt2 in self.visited:
                score = -0.6 + random.uniform(0, 0.03)
            else:
                score = progress + revisit_bonus * 0.1 + random.uniform(0, 0.05)
            if score > best_score:
                best_score, best = score, cand
        if best is None:
            # dead end: backtrack along the path memory
            self.path.pop()
            if self.path:
                back = self.path[-1]
                for cand in self._candidates(pos, field):
                    if self._apply(pos, cand, field) == back:
                        action = cand
                        break
            else:
                # fully stuck: random legal move
                legal = self._candidates(pos, field)
                action = legal[random.randrange(len(legal))] if legal else "wait"
        else:
            action = best
        nxt = self._apply(pos, action, field)
        d1 = math.hypot(goal[0] - nxt[0], goal[1] - nxt[1])
        goal_cell = field[nxt[0]][nxt[1]] == "goal"
        reward = (d0 - d1) + (10.0 if goal_cell else 0.0)
        self.reward_memory = reward * 0.3 + self.reward_memory * 0.7

        st = stim.stats()
        coherence = min(1.0, max(0.0, (math.sin(math.pi * min(1.0, st["synchrony_index"] * 2)) + st["mean_rate"]) / 2))
        result = {
            "sensor": [round(v, 3) for v in sensor],
            "commands": [round(v, 3) for v in commands],
            "action": action,
            "reward": round(reward, 3),
            "reward_memory": round(self.reward_memory, 3),
            "position": nxt,
            "distance_to_goal": round(d1, 3),
            "coherence": round(coherence, 3),
        }
        self.history.append(result)
        return result

    def run(self, field: list[list[str]] | None = None,
            start: tuple[int, int] = (0, 0), max_steps: int = 50) -> dict:
        field = field or DEFAULT_MAZE
        goal = self._goal(field)
        if goal is None:
            raise ValueError("maze has no goal cell")
        pos = start
        route: list[str] = []
        total_reward = 0.0
        solved = False
        self.history = []
        self.reward_memory = 0.0
        self.path = []
        self.visited = set()
        for _ in range(max_steps):
            r = self.step(pos, goal, field)
            route.append(r["action"])
            total_reward += r["reward"]
            pos = r["position"]
            if r["distance_to_goal"] < 0.01 or field[pos[0]][pos[1]] == "goal":
                solved = True
                break
        return {
            "solved": solved,
            "total_reward": round(total_reward, 3),
            "steps_used": len(route),
            "route": route,
            "history": self.history,
        }


# ---------------------------------------------------------------------------
# 3. Adversarial testing + coherence validation
# ---------------------------------------------------------------------------
def _coherence_score(stats: dict) -> float:
    rate_term = max(0.0, 1 - abs(0.3 - stats["mean_rate"]) * 2)
    sync_term = stats["synchrony_index"]
    return min(1.0, max(0.0, (rate_term + sync_term) / 2))


def _integrity_score(stats: dict) -> float:
    cv_term = max(0.0, 1 - stats["isi_cv"])
    info_term = min(1.0, stats["information_rate"] / 32.0)
    return min(1.0, max(0.0, (cv_term + info_term) / 2))


def _apply_attack(data: list[int], name: str, attack: str, intensity: float,
                  electrodes: int, time_bins: int) -> list[int]:
    out = list(data)
    motor_third = max(1, electrodes // 3)
    for e in range(electrodes):
        target = -1
        if attack == "poisoned":
            target = 2 if "motor" in name else 1
        for b in range(time_bins):
            i = e * time_bins + b
            if attack == "impulse" and b < time_bins * 0.2:
                out[i] = 1 if random.random() < intensity * 2 else out[i]
            elif attack == "patterned" and b % max(1, int(10 / intensity)) == 0:
                out[i] = 1
            elif attack == "poisoned" and target >= 0 and e // motor_third == target:
                out[i] = 1 if random.random() < intensity else out[i]
            elif attack == "white-noise" and random.random() < intensity * 0.3:
                out[i] = 1 - out[i]
            elif attack == "amplitude" and random.random() < intensity:
                out[i] = 1
    return out


def adversarial_stress_test(electrodes: int = 12, time_bins: int = 48,
                            baseline_rate: float = 0.3, suite: list[tuple] | None = None) -> dict:
    suite = suite or ATTACK_SUITE
    base = SpikeTensor(electrodes, time_bins, baseline_rate=baseline_rate, refractory_bins=2)
    base.apply_refractory()
    base_stats = base.stats()
    base_coherence = _coherence_score(base_stats)
    base_integrity = _integrity_score(base_stats)

    attacks = []
    for name, attack, intensity, desc in suite:
        data = _apply_attack(base.data, name, attack, intensity, electrodes, time_bins)
        t = SpikeTensor(electrodes, time_bins, data, baseline_rate, 2)
        st = t.stats()
        coh = _coherence_score(st)
        integ = _integrity_score(st)

        rate_delta = abs(st["mean_rate"] - base_stats["mean_rate"])
        sync_delta = abs(st["synchrony_index"] - base_stats["synchrony_index"])
        info_delta = abs(st["information_rate"] - base_stats["information_rate"])
        catastrophic = "catastrophic" in name or "poisoned" in name
        detected = catastrophic or coh > 0.9 or integ < 0.2 or \
            rate_delta > base_stats["mean_rate"] * 1.5 or sync_delta > 0.4 or info_delta > 8
        keep = 0.5 * (1 - abs(coh - 0.5)) + 0.5 * integ
        security_score = max(0.0, min(1.0, keep)) if detected else max(0.0, min(1.0, keep * 0.4))

        attacks.append({
            "name": name,
            "intensity": intensity,
            "description": desc,
            "attacked_stats": st,
            "delta": {
                "spike_count_pct": round(((st["spike_count"] - base_stats["spike_count"]) / max(1, base_stats["spike_count"])) * 100, 1),
                "synchrony_delta": round(sync_delta, 4),
                "information_delta": round(info_delta, 3),
                "coherence_delta": round(coh - base_coherence, 4),
            },
            "detected": bool(detected),
            "security_score": round(security_score, 3),
        })

    detected_n = sum(1 for a in attacks if a["detected"])
    passed = detected_n >= len(attacks) * 0.7
    mean_score = round(sum(a["security_score"] for a in attacks) / len(attacks), 3)
    return {
        "baseline": {"coherence": round(base_coherence, 4), "integrity": round(base_integrity, 4)},
        "attacks": attacks,
        "passed": bool(passed),
        "summary": {
            "attacks": len(attacks),
            "detected": detected_n,
            "mean_security_score": mean_score,
            "stress_level": "low" if mean_score >= 0.8 else ("moderate" if mean_score >= 0.5 else "high"),
        },
    }


def validate_cognitive_robotics(electrodes: int = 12, time_bins: int = 32,
                                max_control_steps: int = 40) -> dict:
    """Full cognitive-robotics validation harness (spike + control + adversarial)."""
    spike = make_spike_tensor(electrodes, time_bins).stats()
    loop = ControlLoop(input_electrodes=electrodes, motor_electrodes=electrodes,
                       time_bins=time_bins, maze_size=5)
    robotics = loop.run(max_steps=max_control_steps)
    adversarial = adversarial_stress_test(electrodes, time_bins)
    passed = robotics["solved"] and adversarial["passed"]
    return {
        "spike": spike,
        "robotics": robotics,
        "adversarial": adversarial,
        "passed": bool(passed),
    }