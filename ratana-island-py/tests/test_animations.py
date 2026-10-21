"""Unit tests for Animation Controller and State Machine."""

from ratana_island.ui.animations import (
    AnimationController,
    IslandState,
    ease_in_out_cubic,
    ease_out_cubic,
    ease_out_quad,
    linear,
)


def test_easing_curves():
    easings = [ease_out_cubic, ease_in_out_cubic, ease_out_quad, linear]
    for fn in easings:
        # Boundary checks
        assert fn(0.0) == 0.0
        assert fn(1.0) == 1.0
        # Clamping
        assert fn(-0.5) == 0.0
        assert fn(1.5) == 1.0
        # Monotonicity
        prev = 0.0
        for step in range(1, 11):
            t = step / 10.0
            val = fn(t)
            assert val >= prev
            prev = val


def test_island_state_values():
    assert IslandState.IDLE.value == "idle"
    assert IslandState.COMPACT.value == "compact"
    assert IslandState.EXPANDING.value == "expanding"
    assert IslandState.EXPANDED.value == "expanded"
    assert IslandState.COLLAPSING.value == "collapsing"
    assert IslandState.NOTIFICATION.value == "notification"
    assert IslandState.MEDIA_CHANGED.value == "media_changed"


def test_animation_controller_step():
    frames = []

    def on_frame(w, h, p):
        frames.append((w, h, p))

    completed_states = []

    def on_complete(state):
        completed_states.append(state)

    ctrl = AnimationController(
        on_frame=on_frame,
        on_complete=on_complete,
        duration_ms=300,
        reduced_motion=False,
    )
    ctrl.current_width = 280.0
    ctrl.current_height = 38.0

    # Start expanding to 460x230
    ctrl.animate_to(460, 230, IslandState.EXPANDED)
    assert ctrl.state == IslandState.EXPANDING
    assert ctrl.target_width == 460.0
    assert ctrl.target_height == 230.0

    # Step through progress
    ctrl.step(0.0)
    assert frames[-1][0] == 280
    assert frames[-1][1] == 38

    ctrl.step(0.5)
    mid_w, mid_h, _ = frames[-1]
    assert 280 < mid_w < 460
    assert 38 < mid_h < 230

    ctrl.step(1.0)
    assert frames[-1][0] == 460
    assert frames[-1][1] == 230


def test_interruptible_retargeting():
    frames = []

    def on_frame(w, h, p):
        frames.append((w, h, p))

    ctrl = AnimationController(
        on_frame=on_frame,
        duration_ms=300,
        reduced_motion=False,
    )
    ctrl.current_width = 280.0
    ctrl.current_height = 38.0

    # 1. Start expanding
    ctrl.animate_to(460, 230, IslandState.EXPANDED)
    ctrl.step(0.5)
    captured_w = ctrl.current_width
    captured_h = ctrl.current_height

    # 2. Interrupt midway and collapse back to 280x38
    ctrl.animate_to(280, 38, IslandState.COMPACT)
    assert ctrl.state == IslandState.COLLAPSING
    assert ctrl.start_width == captured_w
    assert ctrl.start_height == captured_h

    # Step to start of new animation: must match interrupted position, no jumping!
    ctrl.step(0.0)
    assert abs(ctrl.current_width - captured_w) < 1.0

    # Step to end
    ctrl.step(1.0)
    assert ctrl.current_width == 280.0
    assert ctrl.current_height == 38.0


def test_reduced_motion_mode():
    frames = []
    completed = []

    ctrl = AnimationController(
        on_frame=lambda w, h, p: frames.append((w, h, p)),
        on_complete=lambda s: completed.append(s),
        duration_ms=300,
        reduced_motion=True,
    )
    ctrl.current_width = 280.0
    ctrl.current_height = 38.0

    ctrl.animate_to(460, 230, IslandState.EXPANDED)
    # With reduced motion, finishes immediately
    assert ctrl.current_width == 460.0
    assert ctrl.current_height == 230.0
    assert ctrl.state == IslandState.EXPANDED
    assert len(completed) == 1
    assert completed[0] == IslandState.EXPANDED
