from app.ui.pages.review_page import ReviewPage


def _report_dict() -> dict:
    return {
        "title": "Simple Harmonic Motion",
        "sections": [
            {
                "heading": "Objective",
                "body_markdown": "Body text.",
                "word_count": 2,
                "citations": [],
            }
        ],
        "references": [],
    }


def test_review_page_flags_inconclusive_evaluation(qtbot):
    page = ReviewPage()
    qtbot.addWidget(page)

    page.load_review_data(
        _report_dict(),
        {
            "status": "inconclusive",
            "overall_passed": False,
            "failed_sections": [],
            "general_feedback": "Automated evaluation failed with RuntimeError.",
        },
    )

    assert "EVALUATION INCOMPLETE" in page.status_badge.text()
    assert "RuntimeError" in page.eval_details_label.text()


def test_review_page_shows_pass_status_for_passed_evaluation(qtbot):
    page = ReviewPage()
    qtbot.addWidget(page)

    page.load_review_data(
        _report_dict(),
        {"status": "passed", "overall_passed": True, "failed_sections": []},
    )

    assert "PASSED" in page.status_badge.text()
