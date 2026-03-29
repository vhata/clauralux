from __future__ import annotations

from .actions import Action, SendUnits, UpgradeSun
from .config import GameConfig
from .state import GameState, UnitGroup
from .types import NEUTRAL, PlayerId, Position, Tick
from .view import GameView


class Game:
    """The core game simulation. Tick-based, deterministic, zero external deps."""

    def __init__(self, config: GameConfig, state: GameState) -> None:
        self._config = config
        self._state = state
        # Pending actions keyed by player, applied during tick().
        self._pending: dict[PlayerId, list[Action]] = {}

    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def is_over(self) -> bool:
        return self._state.winner is not None

    def get_view(self, player_id: PlayerId) -> GameView:
        return GameView.from_state(self._state, player_id, self._config)

    def apply_actions(self, player_id: PlayerId, actions: list[Action]) -> None:
        """Queue actions from a player. They'll be processed in tick()."""
        if player_id in self._state.eliminated:
            return
        self._pending[player_id] = actions

    def tick(self) -> None:
        """Advance the simulation by one tick.

        Order:
        1. Process pending actions (spawn unit groups, upgrade suns)
        2. Move all unit groups
        3. Resolve arrivals (reinforce or combat)
        4. Produce units at owned suns
        5. Check elimination / win conditions
        6. Increment tick counter
        """
        if self.is_over:
            return

        self._process_actions()
        self._move_unit_groups()
        self._resolve_arrivals()
        self._produce_units()
        self._check_win_condition()
        self._state.tick = Tick(self._state.tick + 1)

    # -- Internal steps --

    def _process_actions(self) -> None:
        for player_id, actions in self._pending.items():
            for action in actions:
                if isinstance(action, SendUnits):
                    self._process_send(player_id, action)
                elif isinstance(action, UpgradeSun):
                    self._process_upgrade(player_id, action)
        self._pending.clear()

    def _process_send(self, player_id: PlayerId, action: SendUnits) -> None:
        sun = self._state.suns.get(action.source_sun_id)
        target = self._state.suns.get(action.target_sun_id)
        if sun is None or target is None:
            return
        if sun.owner != player_id:
            return
        if action.source_sun_id == action.target_sun_id:
            return
        if action.count <= 0:
            return

        # Clamp to available garrison.
        actual_count = min(action.count, int(sun.garrison))
        if actual_count <= 0:
            return

        sun.garrison -= actual_count

        # Compute velocity toward target.
        dx, dy = sun.position.direction_to(target.position)
        speed = self._config.unit_speed

        self._state.add_unit_group(
            UnitGroup(
                owner=player_id,
                count=actual_count,
                position=Position(sun.position.x, sun.position.y),
                target_sun_id=action.target_sun_id,
                velocity_x=dx * speed,
                velocity_y=dy * speed,
            )
        )

    def _process_upgrade(self, player_id: PlayerId, action: UpgradeSun) -> None:
        sun = self._state.suns.get(action.sun_id)
        if sun is None:
            return
        if sun.owner != player_id:
            return
        if sun.level >= self._config.max_sun_level:
            return

        cost_index = sun.level - 1
        if cost_index >= len(self._config.upgrade_costs):
            return
        cost = self._config.upgrade_costs[cost_index]

        if int(sun.garrison) < cost:
            return

        sun.garrison -= cost
        sun.level += 1

    def _move_unit_groups(self) -> None:
        for group in self._state.unit_groups:
            target = self._state.suns.get(group.target_sun_id)
            if target is None:
                continue
            group.position = Position(
                group.position.x + group.velocity_x,
                group.position.y + group.velocity_y,
            )

    def _resolve_arrivals(self) -> None:
        arrived: list[UnitGroup] = []
        remaining: list[UnitGroup] = []

        for group in self._state.unit_groups:
            target = self._state.suns.get(group.target_sun_id)
            if target is None:
                # Target sun doesn't exist — discard the group.
                continue
            dist = group.position.distance_to(target.position)
            if dist <= self._config.unit_speed:
                arrived.append(group)
            else:
                remaining.append(group)

        self._state.unit_groups = remaining

        for group in arrived:
            target = self._state.suns[group.target_sun_id]
            if group.owner == target.owner:
                # Reinforce.
                target.garrison += group.count
            else:
                # Attack.
                damage = group.count * self._config.attack_ratio
                target.garrison -= damage
                if target.garrison <= 0:
                    # Captured!
                    remaining_units = abs(target.garrison) / self._config.attack_ratio
                    target.owner = group.owner
                    target.garrison = remaining_units
                    target.production_ticks = 0
                    if self._config.capture_level_reset is not None:
                        target.level = self._config.capture_level_reset

    def _produce_units(self) -> None:
        cfg = self._config
        for sun in self._state.suns.values():
            if sun.owner == NEUTRAL:
                continue
            sun.production_ticks += 1
            # Produce (level * production_per_level) units every production_interval ticks.
            ticks_per_unit = cfg.production_interval // max(sun.level * cfg.production_per_level, 1)
            if ticks_per_unit > 0 and sun.production_ticks >= ticks_per_unit:
                sun.garrison += 1
                sun.production_ticks = 0

    def _check_win_condition(self) -> None:
        for player_id in self._state.players:
            if player_id in self._state.eliminated:
                continue
            owns_suns = any(s.owner == player_id for s in self._state.suns.values())
            has_groups = any(g.owner == player_id for g in self._state.unit_groups)
            if not owns_suns and not has_groups:
                self._state.add_eliminated(player_id)

        active = [p for p in self._state.players if p not in self._state.eliminated]

        if len(active) == 1:
            self._state.winner = active[0]
        elif len(active) == 0:
            self._state.winner = NEUTRAL  # draw
        elif self._config.max_ticks is not None and self._state.tick >= self._config.max_ticks:
            self._state.winner = NEUTRAL  # draw by timeout
