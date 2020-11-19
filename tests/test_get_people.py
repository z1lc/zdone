import pytest

from app.card_generation.people_getter import Person, get_wikipedia_info, _get_known_for_html, _looks_like_name


class TestPerson(Person):

    def __init__(self, name):
        super().__init__(name, "Some Title", "Some Author")

class TestGetPeople:

    @pytest.mark.skip(reason="integration")
    def test_finds_all_famous_people(self):
        famous_names = ["LeBron James",
                        "Elon Musk",
                        "Abraham Lincoln",
                        "Gandhi",
                        "Martin Luther King",
                        "Michael Jordan",
                        "Donald Trump",
                        "Donald Trump Jr.",
                        "Lance Armstrong",
                        "George Boole",
                        "Oprah Winfrey",
                        "Nehru"]
        people = [TestPerson(name) for name in famous_names]
        wikipedia_people = [get_wikipedia_info(person) for person in people]
        assert(len(list(filter(lambda person: person is None, wikipedia_people))) == 0)

    def test_known_for_html_sensible(self):
        sample_summary_text = """
        LeBron Raymone James Sr. ( lə-BRON; born December 30, 1984) is an American professional basketball player for the Los Angeles Lakers of the National Basketball Association (NBA). Widely considered one of the greatest NBA players, James is frequently compared to Michael Jordan in debates over the greatest basketball player of all time. Playing on the Cleveland Cavaliers, Miami Heat, and Los Angeles Lakers, James is the only player in NBA history to have brought NBA championships to three franchises as Finals MVP.  He has competed in ten NBA Finals, including eight consecutive with the Heat and Cavaliers from 2011 through 2018. His accomplishments include four NBA championships, four NBA Most Valuable Player (MVP) Awards, four Finals MVP Awards, and two Olympic gold medals.  During his 17-year career, James holds the record for all-time playoffs points, is third in all-time points, and eighth in career assists. James has been selected to the All-NBA First Team a record thirteen times, made the All-Defensive First Team five times, and has played in sixteen All-Star Games, in which he was selected All-Star MVP three times.
James played basketball for St. Vincent–St. Mary High School in his hometown of Akron, Ohio, where he was heavily touted by the national media as a future NBA superstar. A prep-to-pro, he was selected by Cleveland with the first overall pick of the 2003 NBA draft. Named the 2003–04 NBA Rookie of the Year, he soon established himself as one of the league's premier players, winning the NBA MVP Award in 2009 and 2010. After failing to win a championship with Cleveland, James left in 2010 to sign as a free agent with Miami. This move was announced in an ESPN special titled The Decision, and is one of the most controversial free agent decisions in sports history.
James won his first two NBA championships while playing for the Heat in 2012 and 2013; in both of these years, he also earned league MVP and Finals MVP. After his fourth season with the Heat in 2014, James opted out of his contract to re-sign with the Cavaliers. In 2016, he led the Cavaliers to victory over the Golden State Warriors in the NBA Finals by coming back from a 3–1 deficit, delivering the franchise's first championship and ending Cleveland's 52-year professional sports title drought. In 2018, James opted out of his contract with the Cavaliers to sign with the Lakers, where he won the 2020 championship and was awarded his fourth Finals MVP.
Off the court, James has accumulated additional wealth and fame from numerous endorsement contracts. He has been featured in books, documentaries, television commercials, and has hosted the ESPY Awards and Saturday Night Live. In 2015, he appeared in the film Trainwreck. James is also an activist for various causes, including fighting for racial equality, improving the lives of African-American communities, and improving education for students. The LeBron James Family Foundation charity builds upon his vision to improve education for students in Akron, Ohio.
"""
        expected_known_for_html = "<ul>\n" + \
            "<li>American professional basketball player for the Los Angeles Lakers of the National Basketball Association</li>\n" + \
            "<li>frequently compared to Michael Jordan in debates over the greatest basketball player of all time</li>\n" + \
            "<li>only player in NBA history to have brought NBA championships to three franchises as Finals MVP</li>" + \
            "</ul>"
        assert(_get_known_for_html(sample_summary_text, "LeBron James") == expected_known_for_html)

    def test_elon_html_sensible(self):
        sample_summary_text = """
        Elon Reeve Musk FRS (/ˈiːlɒn/; born June 28, 1971) is a business magnate, industrial designer, engineer, and philanthropist. He is the founder, CEO, CTO and chief designer of SpaceX; early investor, CEO and product architect of Tesla, Inc.; founder of The Boring Company; co-founder of Neuralink; and co-founder and initial co-chairman of OpenAI. He was elected a Fellow of the Royal Society (FRS) in 2018. Also that year, he was ranked 25th on the Forbes list of The World's Most Powerful People, and was ranked joint-first on the Forbes list of the Most Innovative Leaders of 2019. As of November 15, 2020, his net worth is estimated by Forbes to be US$90.8 billion, making him the 7th richest person in the world. He is also the longest tenured CEO of any automotive manufacturer globally.
        """
        expected_known_for_html = "<ul>\n" + \
            "<li>business magnate, industrial designer, engineer, and philanthropist</li>\n" + \
            "<li>founder, CEO, CTO and chief designer of SpaceX; early investor, CEO and product architect of Tesla, Inc.; founder of The Boring Company; co-founder of Neuralink; and co-founder and initial co-chairman of OpenAI</li>\n" + \
            "<li>elected a Fellow of the Royal Society in 2018</li>" + \
            "</ul>"
        assert(_get_known_for_html(sample_summary_text, "Elon Musk") == expected_known_for_html)

    def test_looks_like_name(self):
        assert(_looks_like_name("Martin Luther King Jr."))
        assert(_looks_like_name("J. P. Beauregard"))
        assert(_looks_like_name("John Smith"))
        assert(_looks_like_name("LeBron Raymone James Sr."))
        assert(not _looks_like_name("NBA"))
        assert(not _looks_like_name("a cool car"))
