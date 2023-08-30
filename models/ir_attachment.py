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

ATTACHMENTS_TO_CHECK_SQL = """SELECT 
    id, name, res_model, res_field, res_id,  store_fname, checksum, mimetype, 
    LENGTH(db_datas) AS db_datas_len, 
    create_uid 
FROM ir_attachment 
ORDER BY id OFFSET %s LIMIT %s;"""


class InoukIRAttachment(models.Model):
    _inherit = "ir.attachment"

    ikas_is_file_storage_broken = fields.Boolean(
        "Is File Broken ?",
        help="When checked, file cannot be read!"
    )

    def btn_check_file(self):
        """ Try to open file. """
        self.ensure_one()
        if not self.store_fname:
            _logger.info("No filename on %s.", self)
            return
        _r = self._file_read(self.store_fname, bin_size=True)
        if not _r:
            self.ikas_is_file_storage_broken = True
        else:
            self.ikas_is_file_storage_broken = False

    @processor_method(processor_visibility_timeout=600)
    def check_file_attachments_storage_batch(self, ids, _imq_logger=None):
        """Check a batch of File Attachments Storage for missing files.
        """
        _task_logger = _imq_logger or _logger
        broken_attachment_ids = []
        _task_logger.info("Checking attachements: %s", ids)
        attachment_to_check_objs = self.sudo().browse(ids)
        for attachment_obj in attachment_to_check_objs:
            if attachment_obj.store_fname and not attachment_obj.datas:
                _task_logger.error("Attachment %s file is not reachable", attachment_obj)
                broken_attachment_ids.append(attachment_obj.id)
            else:
                _task_logger.info("Attachment %s file checked with no error.", attachment_obj)
        _task_logger.info("%s 'ir.attachment' checked.", len(attachment_to_check_objs))
        if broken_attachment_ids:
            _task_logger.error("Broken attachement ids: %s", broken_attachment_ids)
            self.browse(broken_attachment_ids).write({"ikas_is_file_storage_broken": True})
        return broken_attachment_ids

    @processor_method(processor_visibility_timeout=120)
    def check_file_attachments_storage(self, _imq_logger=None):
        """Check File Attachments Storage"""
        _task_logger = _imq_logger or _logger
        _batch_size = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'ik.ir_attachment_migration_batch_size', 
                '50'
            )
        )

        idx = 0
        while True:
            _r = self.env.cr.execute(ATTACHMENTS_TO_CHECK_SQL, (idx * _batch_size, _batch_size))
            _r = self.env.cr.fetchall()
            _ids = [_e[0] for _e in _r]
            if not _r: break 
            _task_logger.info("Launch file attachment check for batch of _ids:%s", _ids)
            self.check_file_attachments_storage_batch.run_async(self, _ids)
            idx += 1
        _task_logger.info("%s check batches launched.", idx)
        return 

    @api.model
    def launch_check_file_attachments_storage(self):
        self.check_file_attachments_storage.run_async(self)

    @processor_method(processor_visibility_timeout=600)
    def migrate_attachment_batch(self, ids, _imq_logger=None):
        """Migrate a batch of attachments.
        """
        _task_logger = _imq_logger or _logger
        _storage = self._storage()  # get value of ir.parameter
        attachment_objs = self.sudo().browse(ids)
        for idx, attachment_obj in enumerate(attachment_objs, start=1):
            _task_logger.info(
                "Migrate Attachment %s (%s/%s) to '%s' storage.",
                attachment_obj,
                idx,
                len(attachment_objs),
                _storage
            )
            attachment_obj.write({
                "datas": attachment_obj.datas, 
                "mimetype": attachment_obj.mimetype
            })
        _task_logger.info("Finished migration to storage:'%s' of %s ", _storage, attachment_objs)

    def btn_migrate(self):
        self.migrate()

    @processor_method(processor_visibility_timeout=600)
    def migrate_all_attachments(self, run_async:bool=True, _imq_logger=None):
        """ Move all attachments into currently configured storage 
        Called by 'Move all Attachments to Specified Storage' button.
        """
        _task_logger = _imq_logger or _logger
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))

        _storage = self._storage()  # get valeu of ir.parameter
        if not _storage in ATTACHMENT_LOCATION_LISTS:
            return super(IrAttachment, self).force_storage()

        _batch_size = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'ik.ir_attachment_migration_batch_size', 
                '50'
            )
        )
        ATTACHMENTS_TO_MOVE_SQL = {
            'db': "SELECT id FROM ir_attachment WHERE store_fname IS NOT NULL ORDER BY id OFFSET %s LIMIT %s;",
            'file': "SELECT id FROM ir_attachment WHERE db_datas IS NOT NULL ORDER BY id OFFSET %s LIMIT %s;",
        }[_storage]
        _task_logger.info("Starting migration of all attachments to storage:'%s'.", _storage)

        idx = 0
        while True:
            _r = self.env.cr.execute(ATTACHMENTS_TO_MOVE_SQL, (idx * _batch_size, _batch_size))
            _r = self.env.cr.fetchall()
            _ids = [_e[0] for _e in _r]
            if not _r: break 
            _task_logger.info("Launch attachments for batch of _ids:%s", _ids)
            if run_async:
                self.migrate_attachment_batch.run_async(self, _ids)
            else:
                self.migrate_attachment_batch(_ids)

            idx += 1
        _task_logger.info("%s move batches launched.", idx)
        return 

    @api.model
    def move_all_attachments_to_storage(self, run_async:bool=True):
        """ Launches migration of all attachments into currently configured storage 
        Called by 'Move all Attachments to Specified Storage' button.
        """
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))
        if run_async:
            _r = self.sudo().migrate_all_attachments.run_async(self)
        else:
            _r = self.sudo().migrate_all_attachments()
        return _r


    @api.model
    def initial_move_all_attachments_to_storage(self, location:str):
        """ Set value of ir.attachment.location then migrate all attachment to specified storage.
        This method does not use queue engine so by design it must be called on a reduced set of attachment.
        That's why it should only be used for initial setup.
        """
        if location not in ('file', 'db'):
            raise Exception("Unsupported value for location:'%s' (allowed: 'db', 'file')" % (
                location,
            ))
        _logger.warning("Moving all attachments to '%s'", location)
        _r = self.env["ir.config_parameter"].sudo().set_param(
            "ir_attachment.location", 
            location
        )
        self.flush_recordset()
        
        _r = self.migrate_all_attachments(run_async=False)
        return _r
