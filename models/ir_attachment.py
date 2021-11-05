###################################################################################
#
#    Copyright (c) 2021 Cyril MORISSE (github: cmorisse)
#
#    This file is a part of 'inouk_attachments_storage' addon
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import logging

from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError,AccessError

from odoo.addons.inouk_message_queue.api import processor_method

_logger = logging.getLogger("IKAttachmentStorage")


ATTACHMENT_LOCATION_SELECTION_LISTS = [
    ('file', "File System"),
    ('db', "PostgreSQL Database")
]
ATTACHMENT_LOCATION_LISTS = [
    elem[0] for elem in ATTACHMENT_LOCATION_SELECTION_LISTS
]


class InoukIRAttachment(models.Model):
    _inherit = "ir.attachment"

    @processor_method(processor_visibility_timeout=3600)
    def check_file_attachments_storage(self, _imq_logger=None):
        """Check File Attachments Storage"""
        _task_logger = _imq_logger or _logger
        broken_attachment_ids = []
        for attachment_obj in self.search([]):
            if attachment_obj.store_fname and not record.datas:
                _task_logger.error("Attachment %s file is not reachable", attachment_obj)
                broken_attachment_ids.append(attachment_obj.id)
            else:
                _task_logger.info("Attachment %s checked with no error.", attachment_obj)
        if broken_attachment_ids:
            _task_logger.error("Broken attachement ids: %s", broken_attachment_ids)
        return broken_attachment_ids

    @api.model
    def launch_check_file_attachments_storage(self):
        self.check_file_attachments_storage.run_async(self)

    @api.model
    def move_attachment_to_storage(self, _imq_logger=None):
        """ Overloaded method that 'Force all attachments to be stored in the currently configured 
        storage'. 
        Called by 'Move all Attachments to Specified Storage' button.
        """
        _task_logger = _imq_logger or _logger
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))

        _storage = self._storage()  # get valeu of ir.parameter
        if not _storage in ATTACHMENT_LOCATION_LISTS:
            return super(IrAttachment, self).force_storage()

        # domain to retrieve the attachments to migrate
        attachments_domain = {
            'db': [('store_fname', '!=', False)],
            'file': [('db_datas', '!=', False)],
        }[_storage]

        _batch_size = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'ik.ir_attachment_migration_batch_size', 
                '50'
            )
        )
        attachments_objs = self.search(attachments_domain)
        if attachments_objs:
            _task_logger.info("Start Migration of %s Attachments.", len(attachments_objs))
            attachments_objs.migrate(_batch_size)
        else:
            _task_logger.info("No attachments found to migrate.")
        return True

    # TODO: add inouk_message_queue run_async support
    def migrate(self, batch_size=None, _imq_logger=None):
        _task_logger = _imq_logger or _logger

        if batch_size is None:
            batch_size = 50

        _storage = self._storage()  # get value of ir.parameter
        for idx, attachment_obj in enumerate(self, start=1):
            _task_logger.info(
                "Migrate Attachment %s (%s/%s) to '%s' storage.",
                attachment_obj,
                idx,
                len(self),
                _storage
            )
            attachment_obj.write({
                "datas": attachment_obj.datas, 
                "mimetype": attachment_obj.mimetype
            })
            if (idx % batch_size)==0:
                self.env.cr.commit()

        if idx % batch_size and len(self) > 1:
            self.env.cr.commit()

    def btn_migrate(self):
        self.migrate()