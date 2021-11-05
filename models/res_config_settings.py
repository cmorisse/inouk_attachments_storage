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
from odoo import fields, models

from .ir_attachment import ATTACHMENT_LOCATION_SELECTION_LISTS


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ik_attachment_storage_location = fields.Selection(
        ATTACHMENT_LOCATION_SELECTION_LISTS,
        config_parameter="ir_attachment.location",
        string="Attachment Storage",
        help="Defines where 'attachments' are stored. When undefined 'File system' is used.",
        # self.env['ir.config_parameter'].sudo().get_param('ir_attachment.location')
    )
    ik_attachment_migration_batch_size = fields.Integer(
        config_parameter="ik.ir_attachment_migration_batch_size",
        string="Attachment Migration Batch Size",
        help="Defines the work batch size of 'attachments' when they are migrated to storage. "
             "Default (when unset) is 50."
        # self.env['ir.config_parameter'].sudo().get_param('ik.ir_attachment_migration_batch_size')
    )

    def btn_move_attachment_to_storage(self):
        self.env["ir.attachment"].move_attachment_to_storage()

    def btn_launch_attachment_storage_check(self):
        self.env["ir.attachment"].launch_check_file_attachments_storage()
