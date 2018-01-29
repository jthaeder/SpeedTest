#!/usr/bin/env python
b'This script requires python 3.4'

"""
Run a speedtest entry and add entry to mongoDB collection per location

Use speedtest: https://github.com/fopina/pyspeedtest/blob/master/pyspeedtest.py

Author: Jochen Thaeder <jochen@thaeder.de>
"""

import sys, os
import pymongo
from pymongo import MongoClient

import argparse

import pyspeedtest

from datetime import datetime

##############################################
# -- GLOBAL CONSTANTS

MONGO_SERVER  = '192.168.178.38'
MONGO_SERVER  = 'localhost'
MONGO_DB_NAME = 'SpeedTest'

ADMIN_USER    = 'user_ST_rw'
READONLY_USER = 'user_ST_ro'

COLLECTION_INDICES = {'Location': 'date'}

##############################################

# -- Check for a proper Python Version
if sys.version[0:3] < '3.0':
    print ('Python version 3.0 or greater required (found: {0}).'.format(sys.version[0:5]))
    sys.exit(-1)
if pymongo.__version__[0:3] < '3.0':
    print ('pymongo version 3.0 or greater required (found: {0}).'.format(pymongo.__version__[0:5]))
    sys.exit(-1)

# ----------------------------------------------------------------------------------
class mongoDbUtil:
    """Class to connect to mongoDB and perform actions."""

    # _________________________________________________________
    def __init__(self, args, user = 'none'):
        self.args = args

        # -- Get the password form env
        if user == "none":
            self.user = None
            self.password = ""
        elif user == "admin":
            self.user = ADMIN_USER
            self.password = os.getenv(ADMIN_USER, 'empty')
        else:
            self.user = READONLY_USER
            self.password = os.getenv(READONLY_USER, 'empty')

        if self.password == 'empty':
            print("Password for user {0} at database {1} has not been supplied".format(self.user, MONGO_DB_NAME))
            sys.exit(-1)

        self.today = datetime.today().strftime('%Y-%m-%d')

        # -- Connect
        self._connectDB()

    # _________________________________________________________
    def _connectDB(self):
        """Connect to the NERSC mongoDB using pymongo."""

        if self.user is None:
            self.client = MongoClient('mongodb://{}/{}'.format(MONGO_SERVER, MONGO_DB_NAME))
        else:
            self.client = MongoClient('mongodb://{0}:{1}@{2}/{3}?authSource=admin'.format(self.user, self.password,
                                                                         MONGO_SERVER, MONGO_DB_NAME))

        self.db = self.client[MONGO_DB_NAME]
        # print ("Existing collections:", self.db.collection_names(include_system_collections = False))

    # _________________________________________________________
    def close(self):
        """Close conenction to the NERSC mongoDB using pymongo."""

        self.client.close()
        self.db = ""

    # _________________________________________________________
    def getCollection(self, collectionName = 'DefaultLocation'):
        """Get collection and set index."""

        collection = self.db[collectionName]

        # - For all locations
        if collectionName not in COLLECTION_INDICES:
            coll_index = 'date'

            return collection

        try:
            collection.create_index([(COLLECTION_INDICES[collectionName], pymongo.ASCENDING)], unique=True)
        except KeyError:
            print ("Warning: Collection", collectionName, "not known. Index not created.")
            pass

        return collection

    # _________________________________________________________
    def dropCollection(self, collectionName):
        """Drop collection."""

        self.db[collectionName].drop()

# ----------------------------------------------------------------------------------
class speedTest:
    """Run SpeedTest"""

    # _________________________________________________________
    def __init__(self, args, collection, runs = 5):
        self.args = args
        self.now = datetime.now()

        self.runs = runs
        self.collection = collection

        self.speedTest = pyspeedtest.SpeedTest(runs=self.runs)

    # _________________________________________________________
    def runTest(self):
        """Add new speed test"""

        stats = dict(server=self.speedTest.host)
        stats['runs'] = self.speedTest.runs
        stats['ping'] = self.speedTest.ping()
        stats['download'] = self.speedTest.download()
        stats['upload'] = self.speedTest.upload()
        stats['date'] = datetime.now()

        self.collection.insert_one(stats)

# ____________________________________________________________________________
def main():
    """Initialize and run"""

    # -- Parse Argument
    parser = argparse.ArgumentParser(description='Run speed test')

    parser.add_argument('--location', nargs=1, required=True)
    parser.add_argument('--nruns', nargs=1, type=int, default=5)
    args = parser.parse_args()

    # -- MongoDB connection
    dbUtil = mongoDbUtil("","admin")
    coll = dbUtil.getCollection( args.location[0])

    # -- Run SpeedTest
    sp = speedTest("", coll, args.nruns[0])
    sp.runTest()

# ----------------------------------------------------------------------------------
if __name__ == "__main__":
    """Call main."""

    sys.exit(main())
