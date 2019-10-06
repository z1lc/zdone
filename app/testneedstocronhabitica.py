import datetime
from unittest import TestCase

from mock import patch

from app import taskutils


class TestNeedsToCronHabitica(TestCase):

    @patch('app.taskutils.today')
    def test_needs_to_cron_habitica(self, test_today):
        test_today.return_value = datetime.date(year=2019, month=9, day=8)
        dailys = [
            {'repeat': {'m': True, 't': True, 'w': True, 'th': True, 'f': True, 's': True, 'su': True}, 'challenge': {},
             'group': {'approval': {'required': False, 'approved': False, 'requested': False}, 'assignedUsers': [],
                       'sharedCompletion': 'singleCompletion'}, 'frequency': 'weekly', 'everyX': 1, 'streak': 30,
             'daysOfMonth': [], 'weeksOfMonth': [],
             'nextDue': ['2019-09-09T07:00:00.000Z', '2019-09-10T07:00:00.000Z', '2019-09-11T07:00:00.000Z',
                         '2019-09-12T07:00:00.000Z', '2019-09-13T07:00:00.000Z', '2019-09-14T07:00:00.000Z'],
             'yesterDaily': True, 'history': [{'date': 1565286381317, 'value': -0.9999995634999035},
                                              {'date': 1565286389348, 'value': 0.025957129651267064},
                                              {'date': 1565372991248, 'value': 1.025292185162455},
                                              {'date': 1565468605729, 'value': 1.999360661332548},
                                              {'date': 1565543812979, 'value': 2.9494163163501685},
                                              {'date': 1565630164267, 'value': 3.8766214888747834},
                                              {'date': 1565712995287, 'value': 4.7820557999646915},
                                              {'date': 1565800991353, 'value': 5.66672384144324},
                                              {'date': 1565886167173, 'value': 6.531561989392076},
                                              {'date': 1565965731253, 'value': 7.377444459781695},
                                              {'date': 1566071429002, 'value': 8.205188705363799},
                                              {'date': 1566325014509, 'value': 9.015560238125795},
                                              {'date': 1566439420810, 'value': 9.809276949267245},
                                              {'date': 1566487378149, 'value': 10.587012988342227},
                                              {'date': 1566574159069, 'value': 11.349402254553848},
                                              {'date': 1566657248918, 'value': 12.097041545893312},
                                              {'date': 1566744550602, 'value': 12.830493405648685},
                                              {'date': 1566833554329, 'value': 13.550288700575642},
                                              {'date': 1566928809018, 'value': 14.256928960567501},
                                              {'date': 1567009937114, 'value': 14.950888505856978},
                                              {'date': 1567104309301, 'value': 15.632616384522338},
                                              {'date': 1567184006298, 'value': 16.302538140269693},
                                              {'date': 1567269207014, 'value': 16.96105742804953},
                                              {'date': 1567357009627, 'value': 17.60855749297993},
                                              {'date': 1567434508087, 'value': 18.245402526242078},
                                              {'date': 1567522245039, 'value': 18.87193891004403},
                                              {'date': 1567607264691, 'value': 19.48849636238224},
                                              {'date': 1567703631234, 'value': 20.095388991137437},
                                              {'date': 1567783691360, 'value': 20.692916265998026},
                                              {'date': 1567879002539, 'value': 21.28136391578924},
                                              {'date': 1567927911364, 'value': 21.861173577780807}], 'completed': True,
             'collapseChecklist': False, 'type': 'daily', 'notes': '0.5', 'tags': [], 'value': 21.861173577780807,
             'priority': 1, 'attribute': 'str', 'startDate': '2019-08-07T07:00:00.000Z', 'checklist': [],
             'reminders': [], 'createdAt': '2019-08-08T01:24:59.811Z', 'updatedAt': '2019-09-08T07:31:51.375Z',
             '_id': 'c29ef5fa-f254-47bb-9697-3eab328566f0', 'text': 'Recall Values',
             'userId': '1d89c385-bced-468a-af64-0716530cb102', 'isDue': True,
             'id': 'c29ef5fa-f254-47bb-9697-3eab328566f0'},
            {'repeat': {'m': True, 't': True, 'w': True, 'th': True, 'f': True, 's': True, 'su': True}, 'challenge': {},
             'group': {'approval': {'required': False, 'approved': False, 'requested': False}, 'assignedUsers': [],
                       'sharedCompletion': 'singleCompletion'}, 'frequency': 'weekly', 'everyX': 1, 'streak': 0,
             'daysOfMonth': [], 'weeksOfMonth': [],
             'nextDue': ['Mon Sep 09 2019 00:00:00 GMT-0700', 'Tue Sep 10 2019 00:00:00 GMT-0700',
                         'Wed Sep 11 2019 00:00:00 GMT-0700', 'Thu Sep 12 2019 00:00:00 GMT-0700',
                         'Fri Sep 13 2019 00:00:00 GMT-0700', 'Sat Sep 14 2019 00:00:00 GMT-0700'], 'yesterDaily': True,
             'history': [{'date': 1565286381307, 'value': -1}, {'date': 1565372933103, 'value': -2.025956704627065},
                         {'date': 1565468186088, 'value': -3.079243664446934},
                         {'date': 1565543425311, 'value': -4.1613476764697825},
                         {'date': 1565600071550, 'value': -5.273877801227675},
                         {'date': 1565712753569, 'value': -6.418581707975462},
                         {'date': 1565799537311, 'value': -7.597361314264667},
                         {'date': 1565859682916, 'value': -8.812291414283896},
                         {'date': 1565886569279, 'value': -7.5589416312041395},
                         {'date': 1566071423053, 'value': -8.772676190274943},
                         {'date': 1566320596604, 'value': -10.024754266123779},
                         {'date': 1566402678815, 'value': -11.317656930453623},
                         {'date': 1566441920833, 'value': -9.981201167556016},
                         {'date': 1566574154318, 'value': -11.27266166435177},
                         {'date': 1566574162199, 'value': -9.937745984766812},
                         {'date': 1566658041752, 'value': -8.647722809988485},
                         {'date': 1566803767598, 'value': -9.895798145147353},
                         {'date': 1566833865719, 'value': -8.607160918151802},
                         {'date': 1566928805219, 'value': -7.360382184347085},
                         {'date': 1567098767535, 'value': -8.567956710843806},
                         {'date': 1567183845461, 'value': -9.813483523188118},
                         {'date': 1567184011691, 'value': -8.527561627682184},
                         {'date': 1567269212575, 'value': -7.2833234505169875},
                         {'date': 1567434504677, 'value': -8.488515765917843},
                         {'date': 1567494134841, 'value': -9.731509616333655},
                         {'date': 1567523073299, 'value': -8.448286126959983},
                         {'date': 1567703588559, 'value': -9.689999227179431},
                         {'date': 1567783688235, 'value': -10.971858443515359},
                         {'date': 1567783696724, 'value': -9.647193067376941},
                         {'date': 1567927584120, 'value': -10.927646943154535}], 'completed': False,
             'collapseChecklist': False, 'type': 'daily', 'notes': '5',
             'tags': ['c08fe7f6-598f-48df-81f9-21abcc70c724'], 'value': -10.927646943154535, 'priority': 1,
             'attribute': 'str', 'startDate': '2019-08-07T07:00:00.000Z', 'checklist': [], 'reminders': [],
             'createdAt': '2019-08-08T01:24:37.783Z', 'updatedAt': '2019-09-08T07:26:24.177Z',
             '_id': '672875e6-993c-49dc-9f98-a91af216808c', 'text': 'M+: Shower',
             'userId': '1d89c385-bced-468a-af64-0716530cb102', 'isDue': True,
             'id': '672875e6-993c-49dc-9f98-a91af216808c'}]

        self.assertFalse(taskutils.needs_to_cron_habitica(dailys))

        test_today.return_value = datetime.date(year=2019, month=9, day=9)
        self.assertTrue(taskutils.needs_to_cron_habitica(dailys))
