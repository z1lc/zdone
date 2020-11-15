from unittest import TestCase

from app.card_generation.util import get_template, AnkiCard
from app.models.base import User
from app.util import htmlize_note


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

    # Useful for developing templates and getting quick feedback on what the HTML will actually look like
    def test_render_template_html(self):
        enable_logging = False
        fake_user = User()
        fake_user.api_key = "ASf23452nxSFS"
        fake_user.uses_rsAnki_javascript = True
        for card in AnkiCard: # make this more specific when developing new card type
            # Verify each template renders correctly
            qfmt_ = get_template(card, fake_user)['qfmt']
            afmt_ = get_template(card, fake_user)['afmt']
            if enable_logging:
                print(qfmt_)
                print("----------")
                print(afmt_)
