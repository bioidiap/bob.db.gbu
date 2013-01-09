#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# @author: Manuel Guenther <Manuel.Guenther@idiap.ch>
# @date:   Fri May 11 17:20:46 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Sanity checks for the GBU database.
"""

import os, sys
import random
import unittest
import bob
import xbob.db.gbu

from xbob.db.gbu.models import Client, File

class GBUDatabaseTest(unittest.TestCase):
  """Performs some tests on the GBU database."""

  def test01_clients(self):
    # Tests that the 'clients()', 'client_ids()', 'models()' and 'model_ids()' functions return the desired number of elements
    db = xbob.db.gbu.Database()

    # the protocols training, dev, idiap
    subworlds = db.m_sub_worlds
    protocols = db.m_protocols

    # client counter
    self.assertEqual(len(db.client_ids()), 782)
    self.assertEqual(len(db.clients(groups='world')), 345)
    for subworld in subworlds:
      self.assertEqual(len(db.clients(groups='world', subworld=subworld)), 345)

    self.assertEqual(len(db.clients(groups='dev')), 437)
    for protocol in protocols:
      self.assertEqual(len(db.clients(groups='dev', protocol=protocol)), 437)

    # model counter
    self.assertEqual(len(db.model_ids(protocol_type='gbu', groups='world')), 345)
    self.assertEqual(len(db.model_ids(protocol_type='multi', groups='world')), 345)
    self.assertEqual(len(db.model_ids(protocol_type='gbu', groups='dev')), 3255)
    self.assertEqual(len(db.model_ids(protocol_type='multi', groups='dev')), 437)
    for subworld in subworlds:
      self.assertEqual(len(db.model_ids(protocol_type='multi', groups='world', subworld=subworld)), 345)
    for protocol in protocols:
      self.assertEqual(len(db.model_ids(protocol_type='gbu', groups='dev', protocol=protocol)), 1085)
      self.assertEqual(len(db.model_ids(protocol_type='multi', groups='dev', protocol=protocol)), 437)

    for protocol in protocols:
      # assert that all models of the 'gbu' protocol type
      #  start with "nd1R" or "nd2R", i.e., the file id
      for model in db.models(protocol_type='gbu', protocol=protocol):
        self.assertTrue(isinstance(model, File))
      # assert that all models of the 'multi' protocol type
      #  start with "nd1S", i.e., the client id
      for model in db.models(protocol_type='multi', protocol=protocol):
        self.assertTrue(isinstance(model, Client))


  def test02_objects(self):
    # Tests that the 'objects()' function returns reasonable output
    db = xbob.db.gbu.Database()

    # the training subworlds and the protocols
    subworlds = db.m_sub_worlds
    protocols = db.m_protocols

    for protocol in protocols:
      # The number of files for each purpose is equal to the number of models
      self.assertEqual(len(db.objects(groups='dev', protocol=protocol, purposes='enrol')),
                       len(db.models(protocol_type='gbu', groups='dev', protocol=protocol)))
      self.assertEqual(len(db.objects(groups='dev', protocol=protocol, purposes='probe')),
                       len(db.models(protocol_type='gbu', groups='dev', protocol=protocol)))

    # The following tests might take a while...
    protocol = protocols[0]
    probe_file_count = len(db.objects(protocol_type='gbu', groups='dev', protocol=protocol, purposes='probe'))
    # check that for 'gbu' protocol types, exactly one file per model is returned
    for model_id in random.sample(db.model_ids(protocol_type='gbu', groups='dev', protocol=protocol), 10):
      # assert that there is exactly one file for each enrol purposes per model
      self.assertEqual(len(db.objects(protocol_type='gbu', groups='dev', protocol=protocol, model_ids=[model_id], purposes='enrol')), 1)
      # probe files should always be the same
      self.assertEqual(len(db.objects(protocol_type='gbu', groups='dev', protocol=protocol, model_ids=[model_id], purposes='probe')), probe_file_count)

    # for the 'multi' protocols, there is AT LEAST one file per model (client)
    for model_id in random.sample(db.model_ids(protocol_type='multi', groups='dev', protocol=protocol), 10):
      # assert that there is exactly one file for each enrol purposes per model
      self.assertTrue(len(db.objects(protocol_type='multi', groups='dev', protocol=protocol, model_ids=[model_id], purposes='enrol')) >= 1)
      # probe files should always be the same
      self.assertEqual(len(db.objects(protocol_type='multi', groups='dev', protocol=protocol, model_ids=[model_id], purposes='probe')), probe_file_count)


  def test03_file_ids(self):
    # Tests that the client id's returned by the 'get_client_id_from_file_id()' and 'get_client_id_from_model_id()' functions are correct
    db = xbob.db.gbu.Database()

    # we test only one of the protocols
    protocol = random.sample(db.m_protocols,1)

    # for 'gbu' protocols, get_client_id_from_file_id and get_client_id_from_model_id should return the same value
    for model_id in random.sample(db.model_ids(protocol_type='gbu', groups='dev', protocol=protocol), 10):
      for file in db.objects(protocol_type='gbu', groups='dev', protocol=protocol, model_ids=[model_id], purposes='enrol'):
        self.assertEqual(
              db.get_client_id_from_file_id(file.id),
              db.get_client_id_from_model_id(model_id, protocol_type='gbu'))

    for model_id in random.sample(db.model_ids(protocol_type='multi', groups='dev', protocol=protocol), 10):
      # for 'multi' protocols, get_client_id_from_model_id should return the client id.
      self.assertEqual(db.get_client_id_from_model_id(model_id, protocol_type='multi'), model_id)
      # and also get_client_id_from_file_id should return the model id
      for file in db.objects(protocol_type='multi', groups='dev', protocol=protocol, model_ids=[model_id], purposes='enrol'):
        self.assertEqual(db.get_client_id_from_file_id(file.id), model_id)


  def test04_annotations(self):
    # Tests that the annotations are available for all files
    db = xbob.db.gbu.Database()

    # we test only one of the protocols
    for protocol in random.sample(db.m_protocols, 1):
      files = db.objects(protocol=protocol)
      for file in random.sample(files, 1000):
        annotations = db.annotations(file.id)
        self.assertTrue('leye' in annotations and 'reye' in annotations)
        self.assertEqual(len(annotations['leye']), 2)
        self.assertEqual(len(annotations['reye']), 2)


  def test05_driver_api(self):
    # Tests the functions of the driver API
    from bob.db.script.dbmanage import main
    self.assertEqual( main('gbu dumplist --self-test'.split()), 0 )
    self.assertEqual( main('gbu dumplist --group=dev --subworld=x8 --protocol=Good --purpose=enrol --self-test'.split()), 0 )
    self.assertEqual( main('gbu checkfiles --self-test'.split()), 0 )
    # This function is deprecated, so we don't test it any more.
    #self.assertEqual( main(['gbu', 'create-annotation-files', '-d', '.', '--self-test']), 0 )
    self.assertEqual(main('gbu reverse Target/Original/04542d172 --self-test'.split()), 0)
    self.assertEqual(main('gbu path 513 --self-test'.split()), 0)

