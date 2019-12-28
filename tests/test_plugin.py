# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
from .fixtures import ItemFactory


# session
# -------
class TestBasic(object):

    def test_query_existing(self, client, items):
        response = client.get('/items/{}'.format(items[0].id))
        assert response.status_code == 200
        assert response.json['name'] == items[0].name
        return

    def test_query_new(self, client):
        # other open read permissions
        item = ItemFactory.create(name='test')
        response = client.get('/items/{}'.format(item.id))
        assert response.status_code == 200
        assert response.json['name'] == 'test'
        return
