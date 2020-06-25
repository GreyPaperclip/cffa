import os
class Config(object):
    DBKEY = os.environ.get('MAFM_DBKEY') or 'blankpassword'