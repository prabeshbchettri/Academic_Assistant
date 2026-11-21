
from app.ui.main_window import MainWindow


def test_ui_main_window_smoke(qtbot):
    window = MainWindow(use_mock_llm=True)
    qtbot.addWidget(window)
    window.show()

    assert window.windowTitle().startswith("Academic AI")
    assert window.stack.count() == 6

    # Test navigation to pages
    window._on_nav_clicked(1)  # Input Page
    assert window.stack.currentIndex() == 1

    window._on_nav_clicked(4)  # History Page
    assert window.stack.currentIndex() == 4

    window._on_nav_clicked(5)  # Settings Page
    assert window.stack.currentIndex() == 5
