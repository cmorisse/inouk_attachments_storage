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
{
    "name": "Inouk Attachments Storage (ir.attachments)",
    "summary": """Simple GUI to manage attachments storage locations.""",
    "version": "13.0.1",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "author": "Cyril MORISSE",
    "website": "https://github.com/cmorisse",
    "contributors": ["Cyril MORISSE <cmorisse@boxes3.net>"],
    "depends": ["base_setup", "inouk_message_queue"],
    "data": [
        "views/ir_attachment_views.xml",
        "views/res_config_settings_views.xml",
    ], 
    "application": False,
    "installable": True,
    "auto_install": False,
}