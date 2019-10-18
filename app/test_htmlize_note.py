from unittest import TestCase

from app.ztasks import htmlize_note


class TestHtmlizeNote(TestCase):

    def test_correctly_replaces_links(self):
        self.assertEqual('<a href="https://hckrnews.com/" target="_blank">https://hckrnews.com/</a><br>'
                         '<a href="https://www.google.com/" target="_blank">https://www.google.com/</a><br>'
                         '<a href="https://hckrnews.com/" target="_blank">https://hckrnews.com/</a><br>'
                         '<a href="https://www.facebook.com/" target="_blank">https://www.facebook.com/</a><br>'
                         '<a href="https://hckrnews.com/" target="_blank">https://hckrnews.com/</a>',
                         htmlize_note("""https://hckrnews.com/
https://www.google.com/
https://hckrnews.com/
https://www.facebook.com/
https://hckrnews.com/"""))
