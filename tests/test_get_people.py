from app.card_generation.people_getter import Person, get_wikipedia_info


class TestGetPeople:

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
                        "Oprah Winfrey"]
        people = [Person(name) for name in famous_names]
        wikipedia_people = [get_wikipedia_info(person) for person in people]
        assert(len(list(filter(lambda person: person is None, wikipedia_people))) == 0)

    def test_corrects_basic_typo(self):
        typo_name = Person("Lance Armstrog")
        real_name = Person("Lance Armstrong")
        assert(get_wikipedia_info(typo_name) == get_wikipedia_info(real_name))

    def test_lebron_html_sensible(self):
        expected_known_for_html = "<ul>\n" + \
            "<li>American professional basketball player for the Los Angeles Lakers of the National Basketball Association</li>\n" + \
            "<li>frequently compared to Michael Jordan in debates over the greatest basketball player of all time</li>\n" + \
            "<li>only player in NBA history to have brought NBA championships to three franchises as Finals MVP</li>" + \
            "</ul>"
        assert(get_wikipedia_info(Person("Lebron James")).known_for_html == expected_known_for_html)

    def test_elon_html_sensible(self):
        expected_known_for_html = "<ul>\n" + \
            "<li>business magnate, industrial designer, engineer, and philanthropist</li>\n" + \
            "<li>founder, CEO, CTO and chief designer of SpaceX; early investor, CEO and product architect of Tesla, Inc.; founder of The Boring Company; co-founder of Neuralink; and co-founder and initial co-chairman of OpenAI</li>\n" + \
            "<li>elected a Fellow of the Royal Society in 2018</li>" + \
            "</ul>"
        assert(get_wikipedia_info(Person("Elon Musk")).known_for_html == expected_known_for_html)
