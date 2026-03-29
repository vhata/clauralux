"""A bot whose every decision is controlled by an evolvable genome.

When instantiated without arguments, loads pre-trained weights from disk
(falling back to sensible defaults). During training, pass an explicit
genome list to evaluate a candidate parameter vector.
"""

from __future__ import annotations

from pathlib import Path

from clauralux.engine.actions import Action, SendUnits, UpgradeSun
from clauralux.engine.types import NEUTRAL, SunId
from clauralux.engine.view import GameView, SunView
from clauralux.training.genome import (
    default_genome,
    genome_to_dict,
    load_genome,
)

from .base import Bot

DEFAULT_WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "data" / "evolved_weights.json"


class EvolvedBot(Bot):
    """Parameterized heuristic bot — every threshold and weight is evolvable."""

    def __init__(
        self,
        genome: list[float] | None = None,
        weights_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        if genome is not None:
            raw = genome
        elif weights_path is not None:
            raw = load_genome(weights_path)
        else:
            try:
                raw = load_genome(DEFAULT_WEIGHTS_PATH)
            except FileNotFoundError:
                raw = default_genome()
        self._p = genome_to_dict(raw)

    # ── helpers ────────────────────────────────────────────────────────────

    def _g(self, name: str) -> float:
        return self._p[name]

    def _gi(self, name: str) -> int:
        return max(1, int(self._p[name]))

    # ── main entry point ──────────────────────────────────────────────────

    def decide(self, view: GameView) -> list[Action]:
        act_interval = self._gi("act_interval")
        if view.tick % act_interval != 0:
            return []

        my_suns = view.my_suns()
        if not my_suns:
            self._intent = "No suns. Waiting for the end."
            return []

        reserve = self._g("reserve_per_sun")
        available_per_sun = {s.id: max(0.0, s.garrison - reserve) for s in my_suns}
        total_available = sum(available_per_sun.values())

        if total_available <= 0:
            self._intent = "Building up garrison reserves."
            return []

        # 1. Threat response — reinforce suns under attack.
        threat_actions = self._handle_threats(view, my_suns, available_per_sun)
        if threat_actions:
            return threat_actions

        # 2. Reinforce weak own suns.
        reinforce_actions = self._handle_reinforce(view, my_suns, available_per_sun)
        if reinforce_actions:
            return reinforce_actions

        # 3. Upgrade economy.
        upgrade_actions = self._handle_upgrade(view, my_suns, total_available)
        if upgrade_actions:
            return upgrade_actions

        # 4. Score targets and attack.
        return self._handle_attack(view, my_suns, available_per_sun, total_available)

    # ── threat response ───────────────────────────────────────────────────

    def _handle_threats(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        available: dict[SunId, float],
    ) -> list[Action]:
        threat_response = self._g("threat_response")
        if threat_response < 0.3:
            return []

        w_incoming = self._g("w_enemy_incoming")
        enemy_groups = view.enemy_unit_groups()

        # Find the most threatened of our suns.
        worst_sun: SunView | None = None
        worst_deficit = 0.0
        for sun in my_suns:
            incoming = sum(g.count * w_incoming for g in enemy_groups if g.target_sun_id == sun.id)
            deficit = incoming - sun.garrison
            if deficit > worst_deficit:
                worst_deficit = deficit
                worst_sun = sun

        if worst_sun is None:
            return []

        # Send reinforcements from the nearest sun with spare units.
        best_src: SunView | None = None
        best_dist = float("inf")
        for sun in my_suns:
            if sun.id == worst_sun.id:
                continue
            if available.get(sun.id, 0) <= 0:
                continue
            d = sun.position.distance_to(worst_sun.position)
            if d < best_dist:
                best_dist = d
                best_src = sun

        if best_src is None:
            return []

        send = int(available.get(best_src.id, 0) * self._g("send_fraction"))
        if send <= 0:
            return []

        self._intent = f"Defending Sun {worst_sun.id}! Sending {send} from Sun {best_src.id}."
        return [SendUnits(best_src.id, worst_sun.id, send)]

    # ── reinforce weak suns ───────────────────────────────────────────────

    def _handle_reinforce(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        available: dict[SunId, float],
    ) -> list[Action]:
        if len(my_suns) < 2:
            return []

        reinforce_prob = self._g("reinforce_own")
        threshold = self._g("defensive_garrison_threshold")

        # Use tick as a pseudo-random check to vary behaviour.
        if (view.tick * 7) % 100 >= reinforce_prob * 100:
            return []

        # Find weakest sun below threshold.
        weakest: SunView | None = None
        for sun in my_suns:
            if sun.garrison < threshold and (weakest is None or sun.garrison < weakest.garrison):
                weakest = sun

        if weakest is None:
            return []

        # Send from strongest sun.
        strongest: SunView | None = None
        for sun in my_suns:
            if sun.id == weakest.id:
                continue
            if strongest is None or available.get(sun.id, 0) > available.get(strongest.id, 0):
                strongest = sun

        if strongest is None or available.get(strongest.id, 0) <= 0:
            return []

        send = int(available.get(strongest.id, 0) * self._g("send_fraction") * 0.5)
        if send <= 0:
            return []

        self._intent = (
            f"Reinforcing Sun {weakest.id} ({weakest.garrison} garrison) from Sun {strongest.id}."
        )
        return [SendUnits(strongest.id, weakest.id, send)]

    # ── upgrade economy ───────────────────────────────────────────────────

    def _handle_upgrade(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        total_available: float,
    ) -> list[Action]:
        threshold = self._g("upgrade_threshold")
        max_level = self._gi("max_upgrade_level")
        upgrade_pref = self._g("upgrade_vs_attack")
        eco_duration = self._g("eco_phase_duration")
        no_target_pref = self._g("upgrade_when_no_targets")

        # Boost upgrade preference during early eco phase.
        eco_boost = 0.3 if view.tick < eco_duration else 0.0
        has_targets = bool(view.enemy_suns() or view.neutral_suns())
        no_target_boost = no_target_pref if not has_targets else 0.0

        effective_pref = upgrade_pref + eco_boost + no_target_boost
        if effective_pref < 0.4:
            return []

        # Find best sun to upgrade.
        for sun in sorted(my_suns, key=lambda s: -s.garrison):
            if sun.level >= min(max_level, view.config.max_sun_level):
                continue
            cost_idx = sun.level - 1
            if cost_idx >= len(view.config.upgrade_costs):
                continue
            cost = view.config.upgrade_costs[cost_idx]
            if sun.garrison >= max(threshold, cost):
                self._intent = f"Upgrading Sun {sun.id} (level {sun.level} -> {sun.level + 1})."
                return [UpgradeSun(sun.id)]

        return []

    # ── target scoring and attack ─────────────────────────────────────────

    def _handle_attack(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        available: dict[SunId, float],
        total_available: float,
    ) -> list[Action]:
        targets = [s for s in view.suns if s.owner != view.my_id]
        if not targets:
            self._intent = "All suns are mine."
            return []

        # Pre-compute friendly units already heading to each target.
        friendly_incoming: dict[SunId, int] = {}
        for g in view.my_unit_groups():
            friendly_incoming[g.target_sun_id] = friendly_incoming.get(g.target_sun_id, 0) + g.count

        # Score all targets.
        scored = self._score_targets(view, my_suns, targets, friendly_incoming)
        if not scored:
            self._intent = "No viable targets."
            return []

        max_targets = self._gi("max_targets_per_tick")
        patience = self._g("patience")
        min_ratio = self._g("min_force_ratio")
        eco_duration = self._g("eco_phase_duration")
        early_agg = self._g("early_aggression")

        effective_ratio = min_ratio * patience
        if view.tick < eco_duration:
            effective_ratio *= 1.0 - early_agg * 0.5

        actions: list[Action] = []
        remaining = dict(available)

        for _score, target in scored[:max_targets]:
            needed = max(1.0, target.garrison * effective_ratio)
            current_total = sum(remaining.values())
            if current_total < needed:
                continue

            dispatch = self._dispatch_units(view, my_suns, target, remaining)
            if dispatch:
                actions.extend(dispatch)
                owner_label = f"P{target.owner}" if target.owner != NEUTRAL else "neutral"
                self._intent = (
                    f"Attacking Sun {target.id} ({owner_label}, garrison {target.garrison})."
                )

        if not actions:
            self._intent = "Targets too strong. Waiting for an opening."

        return actions

    def _score_targets(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        targets: list[SunView],
        friendly_incoming: dict[SunId, int],
    ) -> list[tuple[float, SunView]]:
        w_garrison = self._g("w_garrison")
        w_distance = self._g("w_distance")
        w_level = self._g("w_level")
        w_neutral = self._g("w_neutral_bonus")
        w_enemy = self._g("w_enemy_bonus")
        w_friendly = self._g("w_incoming_friendly")
        overkill = self._g("overkill_aversion")
        nsw = min(1.0, max(0.0, self._g("nearest_sun_weight")))

        total_avail = sum(max(0.0, s.garrison - self._g("reserve_per_sun")) for s in my_suns)

        scored: list[tuple[float, SunView]] = []
        for t in targets:
            dists = [s.position.distance_to(t.position) for s in my_suns]
            if not dists:
                continue
            min_dist = min(dists)
            avg_dist = sum(dists) / len(dists)
            effective_dist = nsw * min_dist + (1.0 - nsw) * avg_dist

            # Lower score = better target.
            score = w_garrison * t.garrison
            score += w_distance * effective_dist * 0.01  # scale distance down
            score -= w_level * t.level
            if t.owner == NEUTRAL:
                score -= w_neutral
            else:
                score -= w_enemy

            # Discount targets we already have units heading toward.
            incoming = friendly_incoming.get(t.id, 0)
            score += w_friendly * incoming

            # Penalise overkill (wasting force on a trivially weak target).
            if total_avail > 0 and t.garrison > 0:
                excess = max(0.0, total_avail - t.garrison * 2) / total_avail
                score += overkill * excess

            scored.append((score, t))

        scored.sort(key=lambda x: x[0])
        return scored

    def _dispatch_units(
        self,
        view: GameView,
        my_suns: tuple[SunView, ...],
        target: SunView,
        remaining: dict[SunId, float],
    ) -> list[Action]:
        send_frac = self._g("send_fraction")
        concentrate = self._g("concentrate_vs_split")

        actions: list[Action] = []
        if concentrate > 0.5:
            # Send from nearest sun only.
            nearest = min(
                my_suns,
                key=lambda s: s.position.distance_to(target.position),
            )
            avail = remaining.get(nearest.id, 0)
            count = int(avail * send_frac)
            if count > 0:
                actions.append(SendUnits(nearest.id, target.id, count))
                remaining[nearest.id] = max(0.0, remaining[nearest.id] - count)
        else:
            # Send from all suns.
            for sun in my_suns:
                avail = remaining.get(sun.id, 0)
                count = int(avail * send_frac)
                if count > 0:
                    actions.append(SendUnits(sun.id, target.id, count))
                    remaining[sun.id] = max(0.0, remaining[sun.id] - count)

        return actions
