# -*- coding: utf-8 -*-
#
# Fixtures for administration.
#
# ------------------------------------------------


# imports
# -------
import pytest
import factory
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound
from flask_sqlalchemy import SQLAlchemy
from flask_plugin import Plugin

from . import SANDBOX


# application
# -----------
class Config(object):
    ENV = 'testing'
    TESTING = True
    SQLALCHEMY_ECHO = False
    PROPAGATE_EXCEPTIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/app.db'.format(SANDBOX)
    PLUGIN_DEFAULT_VARIABLE = True


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
plugin = Plugin(app)


@app.route('/items', methods=['GET', 'POST'])
def all():
    if request.method == 'GET':
        items = db.session.query(Item).all()
        return jsonify([dict(id=x.id, name=x.name) for x in items]), 200

    elif request.method == 'POST':
        item = Item(**request.json)
        db.session.add(item)
        db.session.commit()
        return jsonify(id=item.id, name=item.name), 200

    return


@app.route('/items/<int:ident>', methods=['GET', 'PUT', 'DELETE'])
def one(ident):
    item = db.session.query(Item).filter_by(id=ident).first()
    if not item:
        raise NotFound

    if request.method == 'GET':
        return jsonify(id=item.id, name=item.name), 200

    elif request.method == 'PUT':
        for key, value in request.json.items():
            setattr(item, key, value)
        db.session.commit()
        return jsonify(id=item.id, name=item.name), 200

    elif request.method == 'DELETE':
        db.session.delete(item)
        db.session.commit()

    return


# models
# ------
class Item(db.Model):
    __tablename__ = 'item'

    # basic
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)


# factories
# ---------
class ItemFactory(factory.alchemy.SQLAlchemyModelFactory):

    id = factory.Sequence(lambda x: x + 100)
    name = factory.Faker('name')

    class Meta:
        model = Item
        sqlalchemy_session = db.session


# fixtures
# --------
@pytest.fixture(scope='session')
def items(client):

    # roles
    items = [
        ItemFactory.create(name='one'),
        ItemFactory.create(name='two'),
        ItemFactory.create(name='three')
    ]

    yield items

    return
