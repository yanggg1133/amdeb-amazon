# -*- coding: utf-8 -*-

"""
    Intercept record change event by replacing Odoo record change functions
    with new functions. A new functions calls an original one and fires
    an event. The new function signatures are copied from openerp/models.py
"""

from openerp import models, api, SUPERUSER_ID

from ..shared import utility
from ..shared.model_names import PRODUCT_OPERATION_TABLE
from .event import (create_record_event,
                    write_record_event,
                    unlink_record_event)

import logging

_logger = logging.getLogger(__name__)

# first save old methods
original_create = models.BaseModel.create
original_write = models.BaseModel.write
original_unlink = models.BaseModel.unlink


# To make this also work correctly for traditional-style call,
# We need to 1) override @api.returns defined in the BaseModel
# to support old-style api that returns an id
# and 2) check the return value type to get the id
@api.model
@api.returns('self', lambda value: value.id)
def create(self, values):
    # _logger.debug("In create record for model: {} values: {}".format(
    #    self._name, values))

    # because we use the record-style api,
    # the return is always an record
    record = original_create(self, values)

    if record.id and self._name != PRODUCT_OPERATION_TABLE:
        env = self.env(user=SUPERUSER_ID)
        create_record_event.fire(self._name, env, record.id)
    return record


@api.multi
def write(self, values):
    # _logger.debug("In write record for model: {} ids: {}".format(
    #   self._name, self._ids))

    original_write(self, values)

    # many times values is empty, skip it
    if values:
        env = self.env(user=SUPERUSER_ID)
        for record_id in self._ids:
            write_record_event.fire(self._name, env, record_id, values)
    return True


# To make it also work correctly for record-style call,
# we need to apply the decorator here
@api.cr_uid_ids_context
def unlink(self, cr, uid, ids, context=None):
    # _logger.debug("In unlink record for model: {} ids: {}".format(
    #    self._name, ids))

    original_unlink(self, cr, uid, ids, context=context)
    if not utility.is_sequence(ids):
        ids = [ids]

    if context is None:
        context = {}

    env = api.Environment(cr, SUPERUSER_ID, context)
    for record_id in ids:
        unlink_record_event.fire(self._name, env, record_id)
    return True

# replace with interceptors
models.BaseModel.create = create
models.BaseModel.write = write
models.BaseModel.unlink = unlink
