inouk_attachments_storage
=========================

Technical module that extends the general settings view to include the option 
to migrate the attachment storage. 


Installation / Upgrade
======================

To install this addon:
    - download the addon folder and add it to your Odoo addons folder,
    - restart your Odoo Server
    - logon to your Odoo Server with admin account
    - activate Debug Mode
    - go to Apps Menu
    - click on "Update Apps List" menu item
    - find the addon in Kanvan or List view
    - install or upgrade it


Configuration
=============

Go to "Settings", select the "Attachment Storage Location" you want to use. 
Then click on Save.
Finally click on the Yellow button "Move all All Attachments to Specified Storage".  

S3 Storage
__________

To store attachments on S3:

In Settings

    - Select File (as Storage)
    - Define this ENV Vars (adjust depending on your storage, this comes from a working R2 Setup)

IK_IR_ATTACHMENT_S3_BUCKET=filestore-cyril-mpy13cdockerdev-01
IK_IR_ATTACHMENT_S3_ENDPOINT_URL=https://xxxxxxxxxxxxxxxxxxxxx.eu.r2.cloudflarestorage.com
IK_IR_ATTACHMENT_S3_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxxxxxxx
IK_IR_ATTACHMENT_S3_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxx
IK_IR_ATTACHMENT_S3_REGION=auto

Finally click on the Yellow button "Move all All Attachments to Specified Storage" in Settings

Warning !!!

    To enable, create a setting (Config. Parameter):
 
    ik.ir_attachment_s3_enabled = True or true 

    All others values will disable s3.

Author & Maintainer
===================

This module is maintained by Cyril MORISSE (github: cmorisse)

License
=======

This module is licensed under LGPL-3