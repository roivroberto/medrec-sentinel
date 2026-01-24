from __future__ import annotations


def test_build_demo_does_not_crash() -> None:
    from demo.gradio_app import build_demo

    demo = build_demo()
    assert demo is not None
