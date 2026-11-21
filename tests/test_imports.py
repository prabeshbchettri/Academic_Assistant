def test_main_imports() -> None:
    from app.main import main

    assert callable(main)
