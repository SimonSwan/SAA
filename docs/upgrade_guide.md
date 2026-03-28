# Upgrade Guide

## Adding a New Neuromodulator

1. Edit `saa/schemas/neuromodulation.py`:
   - Add the new modulator field to `ModulatorState`

2. Edit `saa/modules/neuromodulation/default.py`:
   - Add the modulator to `_DEFAULTS` with a baseline value
   - Add accumulation logic in `update()` — what drives it up/down
   - Add decay logic — how fast it returns to baseline
   - Add parameter shifts — how it affects other modules

3. Update `saa/modules/action/default.py`:
   - Incorporate the new modulator's parameter shifts in scoring

4. Add tests in `tests/unit/test_neuromodulation.py`

5. Run Swan Test Suite to verify no regressions

## Replacing the Memory Module

1. Implement `MemoryInterface` from `saa/interfaces/memory.py`

2. Required methods:
   - `encode(episode_data)` — store new memories
   - `retrieve(query)` — find relevant memories
   - `decay(tick)` — apply forgetting
   - `get_relational_memory(agent_id)` — trust/betrayal history

3. State migration:
   ```python
   # In your new module's set_state():
   def set_state(self, state):
       if state.version < "0.2.0":
           # Migrate from old format
           ...
   ```

4. Register: `registry.register("memory", YourNewMemory())`

5. Run full test suite, especially:
   - `tests/unit/test_memory.py`
   - `tests/swan/test_grief_persistence.py`
   - `tests/swan/test_betrayal_recovery.py`

## Upgrading Embodiment from Simulated to Robotic

1. Implement `EmbodimentInterface` in a new adapter:
   ```
   saa/adapters/robotic.py → RoboticEmbodimentAdapter
   ```

2. Map hardware signals to the standard body state:
   | Hardware Signal | Body Variable |
   |----------------|---------------|
   | Battery level | energy |
   | CPU/motor temp | temperature |
   | Motor load | strain |
   | Network latency | latency_load |
   | Storage health | memory_integrity |
   | Wear metrics | damage |
   | Charging rate | recovery_rate |
   | Sensor readings | resource_level |

3. Handle sensor failures gracefully:
   - Use last known value with uncertainty flag
   - Emit "sensor_failure" event
   - Interoception layer should detect stale signals

4. Register: `registry.register("embodiment", RoboticEmbodimentAdapter())`

5. Test incrementally:
   - Unit tests for sensor mapping
   - Integration tests with real or simulated hardware
   - Swan Test Suite for behavioral consistency

## Adding New Tests

1. **Unit test**: `tests/unit/test_<module>.py`
   - Test module in isolation
   - Build TickContext manually
   - Assert on ModuleOutput and state changes

2. **Integration test**: `tests/integration/test_<feature>.py`
   - Use `build_full_engine()` from conftest
   - Run multiple ticks
   - Assert on cross-module behavior

3. **Swan test**: `tests/swan/test_<scenario>.py`
   - Use a scenario from `saa/simulations/scenarios.py`
   - Run full simulation
   - Assert on behavioral metrics and trends

## Migrating Saved Agent State

When changing module state schemas:

1. **Backward compatible changes** (adding optional fields):
   - Pydantic handles this automatically with defaults

2. **Breaking changes** (renaming/removing fields):
   - Add version check in `set_state()`:
   ```python
   def set_state(self, state):
       data = state.model_dump()
       if data.get("version", "0.0.0") < "0.2.0":
           data["new_field"] = migrate_old_field(data.pop("old_field", None))
       self._state = MyState(**data)
   ```

3. **Database migration**:
   - Write a migration script that loads all saved states, transforms them, and re-saves
   - Keep the old database as backup

## Checklist for Any Module Upgrade

- [ ] Implements the correct interface
- [ ] State model is serializable (Pydantic)
- [ ] `get_state()` and `set_state()` round-trip correctly
- [ ] Handles version migration for old saved states
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Swan Test Suite passes (especially `test_upgrade_stability`)
- [ ] VERSION is bumped appropriately
- [ ] CAPABILITIES list is updated
- [ ] DEPENDENCIES are accurate
