from asud.ui.app import DissertationReportApp


class FakeTree:
    def __init__(self, selection):
        self._selection = selection

    def selection(self):
        return self._selection


def test_get_selected_record_indexes_combines_checked_rows_and_tree_selection():
    app = DissertationReportApp.__new__(DissertationReportApp)
    app.selected_record_indexes = {3, 1}
    app.tree = FakeTree(("2", "bad"))

    assert app.get_selected_record_indexes() == [1, 2, 3]
