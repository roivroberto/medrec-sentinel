def test_smoke_import() -> None:
    import medrec_sentinel

    # Without an __init__.py, Python may treat this as a namespace package.
    # We want a real package for predictable metadata/exports.
    assert getattr(medrec_sentinel, "__file__", None) is not None
