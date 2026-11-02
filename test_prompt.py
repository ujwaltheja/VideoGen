"""Laptop checks for size, frames and prompt rules. No GPU."""
from prompt_build import (
    build_negative,
    build_prompt,
    clamp_guidance,
    clamp_steps,
    flow_shift,
    resolve_frames,
    resolve_size,
    snap_frames,
)


def test_defaults_match_studio_and_wan():
    assert resolve_size(None, None, None) == (1280, 704)
    assert resolve_size(None, None, "short") == (704, 1280)
    assert resolve_size(None, None, "draft") == (832, 480)
    assert resolve_frames({}, "landscape") == 81
    assert resolve_frames({}, "draft") == 49


def test_explicit_size_wins_and_snaps_to_32():
    assert resolve_size(1000, 500, "draft") == (992, 480)
    assert resolve_size(4000, 10, None) == (1280, 480)
    # Follow the still's aspect inside the landscape area (1280×704).
    w, h = resolve_size(None, None, "landscape", (1216, 832))
    assert w % 32 == 0 and h % 32 == 0
    assert w * h <= 1280 * 704
    assert abs(w / h - 1216 / 832) < 0.05


def test_frames_are_4n_plus_1():
    assert snap_frames(64) == 65
    assert snap_frames(80) == 81
    assert snap_frames(1) == 17
    assert snap_frames(400) == 121
    assert resolve_frames({"seconds": 4}) == 97
    assert resolve_frames({"seconds": 3.375}) == 81
    # Studio Hub body: length is 16 fps frames, image_base64 present, no fps field.
    assert resolve_frames({"length": 64, "image_base64": "x", "cfg": 2.0}) == 97
    # Diffusers-style length is already a 24 fps frame count.
    assert resolve_frames({"length": 81}) == 81


def test_steps_stay_on_the_fast_schedule():
    assert clamp_steps(None) == 8
    assert clamp_steps(50) == 20
    assert clamp_steps(4) == 4
    assert clamp_guidance(None) == 5.0
    assert clamp_guidance(2.0) == 2.0
    assert flow_shift(832, 480) == 3.0
    assert flow_shift(1280, 704) == 5.0


def test_prompt_keeps_the_motion_and_the_lock():
    text = build_prompt("gentle smile, leaves drifting")
    assert text.startswith("gentle smile, leaves drifting")
    assert "do not redraw anyone" in text
    assert "No new people" in text
    long = build_prompt("bounce " * 800)
    assert len(long) < 1600
    neg = build_negative("cartoon blood")
    assert "deformed hands" in neg
    assert "cartoon blood" in neg


if __name__ == "__main__":
    test_defaults_match_studio_and_wan()
    test_explicit_size_wins_and_snaps_to_32()
    test_frames_are_4n_plus_1()
    test_steps_stay_on_the_fast_schedule()
    test_prompt_keeps_the_motion_and_the_lock()
    print("ok")
