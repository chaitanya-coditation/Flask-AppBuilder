import unittest
import os
import string
import random
import datetime
import json
import logging

from nose.tools import eq_, ok_
from flask_appbuilder import SQLA
from .sqla.models import Model1, Model2, insert_data
from flask_appbuilder.models.sqla.filters import \
    FilterGreater, FilterSmaller


log = logging.getLogger(__name__)

MODEL1_DATA_SIZE = 10
MODEL2_DATA_SIZE = 10


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        from flask import Flask
        from flask_appbuilder import AppBuilder
        from flask_appbuilder.models.sqla.interface import SQLAInterface
        from flask_appbuilder.api import ModelApi

        self.app = Flask(__name__)
        self.basedir = os.path.abspath(os.path.dirname(__file__))
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'
        self.app.config['SECRET_KEY'] = 'thisismyscretkey'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        self.db = SQLA(self.app)
        self.appbuilder = AppBuilder(self.app, self.db.session, update_perms=False)
        # Create models and insert data
        insert_data(self.db.session, MODEL1_DATA_SIZE)

        class Model1Api(ModelApi):
            datamodel = SQLAInterface(Model1)
            list_columns = [
                'field_integer',
                'field_float',
                'field_string',
                'field_date'
            ]
            description_columns = {
                'field_integer': 'Field Integer',
                'field_float': 'Field Float',
                'field_string': 'Field String'
            }

        class Model1ApiFieldsInfo(Model1Api):
            datamodel = SQLAInterface(Model1)
            add_columns = [
                'field_integer',
                'field_float',
                'field_string',
                'field_date'
            ]
            edit_columns = [
                'field_string',
                'field_integer'
            ]

        class Model1FuncApi(ModelApi):
            datamodel = SQLAInterface(Model1)
            list_columns = [
                'field_integer',
                'field_float',
                'field_string',
                'field_date',
                'full_concat'
            ]
            description_columns = {
                'field_integer': 'Field Integer',
                'field_float': 'Field Float',
                'field_string': 'Field String'
            }

        class Model1ApiFiltered(ModelApi):
            datamodel = SQLAInterface(Model1)
            base_filters = [
                ['field_integer', FilterGreater, 2],
                ['field_integer', FilterSmaller, 4]
            ]

        self.model1api = Model1Api
        self.appbuilder.add_view_no_menu(Model1Api)
        self.model1funcapi = Model1Api
        self.appbuilder.add_view_no_menu(Model1FuncApi)
        self.model1apifieldsinfo = Model1ApiFieldsInfo
        self.appbuilder.add_view_no_menu(Model1ApiFieldsInfo)
        self.appbuilder.add_view_no_menu(Model1ApiFiltered)

        class Model2Api(ModelApi):
            datamodel = SQLAInterface(Model2)
            list_columns = [
                'group'
            ]
            show_columns = [
                'group'
            ]

        class Model2ApiFilteredRelFields(ModelApi):
            datamodel = SQLAInterface(Model2)
            list_columns = [
                'group'
            ]
            show_columns = [
                'group'
            ]
            add_query_rel_fields = {
                'group': [
                    ['field_integer', FilterGreater, 2],
                    ['field_integer', FilterSmaller, 4]
                ]
            }
            edit_query_rel_fields = add_query_rel_fields

        self.model2api = Model2Api
        self.appbuilder.add_view_no_menu(Model2Api)
        self.model2apifilteredrelfields = Model2ApiFilteredRelFields
        self.appbuilder.add_view_no_menu(Model2ApiFilteredRelFields)

    def tearDown(self):
        self.appbuilder = None
        self.app = None
        self.db = None

    def test_get_item(self):
        """
            REST Api: Test get item
        """
        client = self.app.test_client()

        for i in range(1, MODEL1_DATA_SIZE):
            rv = client.get('api/v1/model1api/{}/'.format(i))
            data = json.loads(rv.data.decode('utf-8'))
            eq_(rv.status_code, 200)
            self.assert_get_item(rv, data, i - 1)

    def assert_get_item(self, rv, data, value):
        eq_(data['result'], {
            'field_date': None,
            'field_float': float(value),
            'field_integer': value,
            'field_string': "test{}".format(value)
        })
        # test descriptions
        eq_(data['description_columns'], self.model1api.description_columns)
        # test labels
        eq_(data['label_columns'], {
            'field_date': 'Field Date',
            'field_float': 'Field Float',
            'field_integer': 'Field Integer',
            'field_string': 'Field String'
        })
        eq_(rv.status_code, 200)

    def test_get_item_select_cols(self):
        """
            REST Api: Test get item with select columns
        """
        client = self.app.test_client()

        for i in range(1, MODEL1_DATA_SIZE):
            rv = client.get('api/v1/model1api/{}/?_c_=field_integer'.format(i))
            data = json.loads(rv.data.decode('utf-8'))
            eq_(data['result'], {'field_integer': i - 1})
            eq_(data['description_columns'], {
                'field_integer': 'Field Integer'
            })
            eq_(data['label_columns'], {
                'field_integer': 'Field Integer'
            })
            eq_(rv.status_code, 200)

    def test_get_item_not_found(self):
        """
            REST Api: Test get item not found
        """
        client = self.app.test_client()
        pk = 11
        rv = client.get('api/v1/model1api/{}/'.format(pk))
        eq_(rv.status_code, 404)

    def test_get_item_base_filters(self):
        """
            REST Api: Test get item with base filters
        """
        client = self.app.test_client()
        # We can't get a base filtered item
        pk = 1
        rv = client.get('api/v1/model1apifiltered/{}/'.format(pk))
        eq_(rv.status_code, 404)
        client = self.app.test_client()
        # This one is ok pk=4 field_integer=3 2>3<4
        pk = 4
        rv = client.get('api/v1/model1apifiltered/{}/'.format(pk))
        eq_(rv.status_code, 200)

    def test_get_item_rel_field(self):
        """
            REST Api: Test get item with with related fields
        """
        client = self.app.test_client()
        # We can't get a base filtered item
        pk = 1
        rv = client.get('api/v1/model2api/{}/'.format(pk))
        data = json.loads(rv.data.decode('utf-8'))
        eq_(rv.status_code, 200)
        eq_(data['result'], {'group': 1})

    def test_get_list(self):
        """
            REST Api: Test get list
        """
        client = self.app.test_client()

        rv = client.get('api/v1/model1api/')
        data = json.loads(rv.data.decode('utf-8'))
        # Tests count property
        eq_(data['count'], MODEL1_DATA_SIZE)
        # Tests data result default page size
        eq_(len(data['result']), self.model1api.page_size)
        for i in range(1, MODEL1_DATA_SIZE):
            self.assert_get_list(rv, data['result'][i - 1], i - 1)

    @staticmethod
    def assert_get_list(rv, data, value):
        eq_(data, {
            'field_date': None,
            'field_float': float(value),
            'field_integer': value,
            'field_string': "test{}".format(value)
        })
        eq_(rv.status_code, 200)

    def test_get_list_order(self):
        """
            REST Api: Test get list order params
        """
        client = self.app.test_client()

        # test string order asc
        rv = client.get('api/v1/model1api/?_o_=field_string:asc')
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_date': None,
            'field_float': 0.0,
            'field_integer': 0,
            'field_string': "test0"
        })
        eq_(rv.status_code, 200)
        # test string order desc
        rv = client.get('api/v1/model1api/?_o_=field_string:desc')
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_date': None,
            'field_float': float(MODEL1_DATA_SIZE - 1),
            'field_integer': MODEL1_DATA_SIZE - 1,
            'field_string': "test{}".format(MODEL1_DATA_SIZE - 1)
        })
        eq_(rv.status_code, 200)

    def test_get_list_page(self):
        """
            REST Api: Test get list page params
        """
        page_size = 5
        client = self.app.test_client()

        # test page zero
        uri = 'api/v1/model1api/?_p_={}:0&_o_=field_integer:asc'.format(page_size)
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_date': None,
            'field_float': 0.0,
            'field_integer': 0,
            'field_string': "test0"
        })
        eq_(rv.status_code, 200)
        eq_(len(data['result']), page_size)
        # test page zero
        uri = 'api/v1/model1api/?_p_={}:1&_o_=field_integer:asc'.format(page_size)
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_date': None,
            'field_float': float(page_size),
            'field_integer': page_size,
            'field_string': "test{}".format(page_size)
        })
        eq_(rv.status_code, 200)
        eq_(len(data['result']), page_size)

    def test_get_list_filters(self):
        """
            REST Api: Test get list filter params
        """
        client = self.app.test_client()
        filter_value = 5
        # test string order asc
        uri = 'api/v1/model1api/?_f_0=field_integer:gt:{}&_o_=field_integer:asc'.format(filter_value)
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_date': None,
            'field_float': float(filter_value + 1),
            'field_integer': filter_value + 1,
            'field_string': "test{}".format(filter_value + 1)
        })
        eq_(rv.status_code, 200)

    def test_get_list_select_cols(self):
        """
            REST Api: Test get list with selected columns
        """
        client = self.app.test_client()
        uri = 'api/v1/model1api/?_c_=field_integer&_o_=field_integer:asc'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['result'][0], {
            'field_integer': 0,
        })
        eq_(data['label_columns'], {
            'field_integer': 'Field Integer'
        })
        eq_(data['description_columns'], {
            'field_integer': 'Field Integer'
        })
        eq_(data['list_columns'], [
            'field_integer'
        ])
        eq_(rv.status_code, 200)

    def test_get_list_base_filters(self):
        """
            REST Api: Test get list with base filters
        """
        client = self.app.test_client()
        uri = 'api/v1/model1apifiltered/?_o_=field_integer:asc'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        expected_result = [
            {
                'field_date': None,
                'field_float': 3.0,
                'field_integer': 3,
                'field_string': 'test3',
                'id': 4
            }
        ]
        eq_(data['result'], expected_result)

    def test_info_filters(self):
        """
            REST Api: Test info filters
        """
        client = self.app.test_client()
        uri = 'api/v1/model1api/info'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        expected_filters = {
            'field_date': [
                {'name': 'Equal to', 'operator': 'eq'},
                {'name': 'Greater than', 'operator': 'gt'},
                {'name': 'Smaller than', 'operator': 'lt'},
                {'name': 'Not Equal to', 'operator': 'neq'}
            ],
            'field_float': [
                {'name': 'Equal to', 'operator': 'eq'},
                {'name': 'Greater than', 'operator': 'gt'},
                {'name': 'Smaller than', 'operator': 'lt'},
                {'name': 'Not Equal to', 'operator': 'neq'}
            ],
            'field_integer': [
                {'name': 'Equal to', 'operator': 'eq'},
                {'name': 'Greater than', 'operator': 'gt'},
                {'name': 'Smaller than', 'operator': 'lt'},
                {'name': 'Not Equal to', 'operator': 'neq'}
            ],
            'field_string': [
                {'name': 'Starts with', 'operator': 'sw'},
                {'name': 'Ends with', 'operator': 'ew'},
                {'name': 'Contains', 'operator': 'ct'},
                {'name': 'Equal to', 'operator': 'eq'},
                {'name': 'Not Starts with', 'operator': 'nsw'},
                {'name': 'Not Ends with', 'operator': 'new'},
                {'name': 'Not Contains', 'operator': 'nct'},
                {'name': 'Not Equal to', 'operator': 'neq'}
            ]
        }
        eq_(data['filters'], expected_filters)

    def test_info_fields(self):
        """
            REST Api: Test info fields (add, edit)
        """
        client = self.app.test_client()
        uri = 'api/v1/model1apifieldsinfo/info'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        expect_add_fields = [
            {
                'description': 'Field Integer',
                'label': 'Field Integer',
                'name': 'field_integer',
                'required': False, 'type': 'Integer'
            },
            {
                'description': 'Field Float',
                'label': 'Field Float',
                'name': 'field_float',
                'required': False,
                'type': 'Float'
            },
            {
                'description': 'Field String',
                'label': 'Field String',
                'name': 'field_string',
                'required': True,
                'type': 'String',
                'validate': ['<Length(min=None, max=50, equal=None, error=None)>']
            },
            {
                'description': '',
                'label': 'Field Date',
                'name': 'field_date',
                'required': False,
                'type': 'Date'
            }
        ]
        expect_edit_fields = list()
        for edit_col in self.model1apifieldsinfo.edit_columns:
            for item in expect_add_fields:
                if item['name'] == edit_col:
                    expect_edit_fields.append(item)
        eq_(data['add_fields'], expect_add_fields)
        eq_(data['edit_fields'], expect_edit_fields)

    def test_info_fields_rel_field(self):
        """
            REST Api: Test info fields with related fields
        """
        client = self.app.test_client()
        uri = 'api/v1/model2api/info'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        expected_rel_add_field = {
                'description': '',
                'label': 'Group',
                'name': 'group',
                'required': False,
                'type': 'Related',
                'values': []
            }
        for i in range(MODEL1_DATA_SIZE):
            expected_rel_add_field['values'].append(
                {
                    'id': i + 1,
                    'value': "test{}".format(i)
                }
            )
        for rel_field in data['add_fields']:
            if rel_field['name'] == 'group':
                eq_(rel_field, expected_rel_add_field)

    def test_info_fields_rel_filtered_field(self):
        """
            REST Api: Test info fields with filtered
            related fields
        """
        client = self.app.test_client()
        uri = 'api/v1/model2apifilteredrelfields/info'
        rv = client.get(uri)
        data = json.loads(rv.data.decode('utf-8'))
        expected_rel_add_field = {
            'description': '',
            'label': 'Group',
            'name': 'group',
            'required': False,
            'type': 'Related',
            'values': [
                {
                    'id': 4,
                    'value': 'test3'
                }
            ]
        }
        for rel_field in data['add_fields']:
            if rel_field['name'] == 'group':
                eq_(rel_field, expected_rel_add_field)
        for rel_field in data['edit_fields']:
            if rel_field['name'] == 'group':
                eq_(rel_field, expected_rel_add_field)

    def test_delete_item(self):
        """
            REST Api: Test delete item
        """
        client = self.app.test_client()
        pk = 2
        rv = client.delete('api/v1/model1api/{}'.format(pk))
        eq_(rv.status_code, 200)
        model = self.db.session.query(Model1).get(pk)
        eq_(model, None)

    def test_delete_item_not_found(self):
        """
            REST Api: Test delete item not found
        """
        client = self.app.test_client()
        pk = 11
        rv = client.delete('api/v1/model1api/{}'.format(pk))
        eq_(rv.status_code, 404)

    def test_delete_item_base_filters(self):
        """
            REST Api: Test delete item with base filters
        """
        client = self.app.test_client()
        # Try to delete a filtered item
        pk = 1
        rv = client.delete('api/v1/model1apifiltered/{}'.format(pk))
        eq_(rv.status_code, 404)

    def test_update_item(self):
        """
            REST Api: Test update item
        """
        client = self.app.test_client()
        pk = 3
        item = dict(
            field_string="test_Put",
            field_integer=0,
            field_float=0.0
        )
        rv = client.put('api/v1/model1api/{}'.format(pk), json=item)
        eq_(rv.status_code, 200)
        model = self.db.session.query(Model1).get(pk)
        eq_(model.field_string, "test_Put")
        eq_(model.field_integer, 0)
        eq_(model.field_float, 0.0)

    def test_update_item_base_filters(self):
        """
            REST Api: Test update item with base filters
        """
        client = self.app.test_client()
        pk = 4
        item = dict(
            field_string="test_Put",
            field_integer=3,
            field_float=3.0
        )
        rv = client.put('api/v1/model1apifiltered/{}'.format(pk), json=item)
        eq_(rv.status_code, 200)
        model = self.db.session.query(Model1).get(pk)
        eq_(model.field_string, "test_Put")
        eq_(model.field_integer, 3)
        eq_(model.field_float, 3.0)
        # We can't update an item that is base filtered
        client = self.app.test_client()
        pk = 1
        rv = client.put('api/v1/model1apifiltered/{}'.format(pk), json=item)
        eq_(rv.status_code, 404)

    def test_update_item_not_found(self):
        """
            REST Api: Test update item not found
        """
        client = self.app.test_client()
        pk = 11
        item = dict(
            field_string="test_Put",
            field_integer=0,
            field_float=0.0
        )
        rv = client.put('api/v1/model1api/{}'.format(pk), json=item)
        eq_(rv.status_code, 404)

    def test_update_val_size(self):
        """
            REST Api: Test update validate size
        """
        client = self.app.test_client()
        pk = 1
        field_string = 'a' * 51
        item = dict(
            field_string=field_string,
            field_integer=11,
            field_float=11.0
        )
        rv = client.put('api/v1/model1api/{}'.format(pk), json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_string'][0], 'Longer than maximum length 50.')

    def test_update_item_val_type(self):
        """
            REST Api: Test update validate type
        """
        client = self.app.test_client()
        pk = 1
        item = dict(
            field_string="test11",
            field_integer="test11",
            field_float=11.0
        )
        rv = client.put('api/v1/model1api/{}'.format(pk), json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_integer'][0], 'Not a valid integer.')

        item = dict(
            field_string=11,
            field_integer=11,
            field_float=11.0
        )
        rv = client.post('api/v1/model1api/', json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_string'][0], 'Not a valid string.')

    def test_create_item(self):
        """
            REST Api: Test create item
        """
        client = self.app.test_client()
        item = dict(
            field_string="test11",
            field_integer=11,
            field_float=11.0,
            field_date=None
        )
        rv = client.post('api/v1/model1api/', json=item)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(rv.status_code, 201)
        eq_(data['result'], item)
        model = self.db.session.query(Model1).filter_by(field_string='test11').first()
        eq_(model.field_string, "test11")
        eq_(model.field_integer, 11)
        eq_(model.field_float, 11.0)

    def test_create_item_val_size(self):
        """
            REST Api: Test create validate size
        """
        client = self.app.test_client()
        field_string = 'a' * 51
        item = dict(
            field_string=field_string,
            field_integer=11,
            field_float=11.0
        )
        rv = client.post('api/v1/model1api/', json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_string'][0], 'Longer than maximum length 50.')

    def test_create_item_val_type(self):
        """
            REST Api: Test create validate type
        """
        client = self.app.test_client()
        item = dict(
            field_string="test11",
            field_integer="test11",
            field_float=11.0
        )
        rv = client.post('api/v1/model1api/', json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_integer'][0], 'Not a valid integer.')

        item = dict(
            field_string=11,
            field_integer=11,
            field_float=11.0
        )
        rv = client.post('api/v1/model1api/', json=item)
        eq_(rv.status_code, 400)
        data = json.loads(rv.data.decode('utf-8'))
        eq_(data['message']['field_string'][0], 'Not a valid string.')

    def test_get_list_col_function(self):
        """
            REST Api: Test get list of objects with columns as functions
        """
        client = self.app.test_client()
        rv = client.get('api/v1/model1funcapi/')
        data = json.loads(rv.data.decode('utf-8'))
        # Tests count property
        eq_(data['count'], MODEL1_DATA_SIZE)
        # Tests data result default page size
        eq_(len(data['result']), self.model1api.page_size)
        for i in range(1, MODEL1_DATA_SIZE):
            item = data['result'][i - 1]
            eq_(item['full_concat'], "{}.{}.{}.{}".format(
                    "test" + str(i - 1),
                    i - 1,
                    float(i - 1),
                    None
                )
            )
