""" Unused file during CFFA development.

TO DO: Purge this file from git.
"""

import os


class Config(object):
    DBKEY = os.environ.get('MAFM_DBKEY') or 'blankpassword'
