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

"""Table models and functionality for the GBU database.
"""

import os
from sqlalchemy import Table, Column, Integer, String, ForeignKey, or_, and_
from bob.db.sqlalchemy_migration import Enum, relationship
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def client_id_from_signature(signature):
  return int(signature[4:])


class Client(Base):
  """The client of the GBU database consists of an integral ID
  as well as the 'signature' as read from the file lists."""
  __tablename__ = 'client'

  id = Column(Integer, primary_key=True)
  signature = Column(String(9), unique=True) # The client signature; should start with nd1

  def __init__(self, signature):
    self.signature = signature
    self.id = client_id_from_signature(signature)

  def __repr__(self):
    return "<Client(%d = '%s')>" % (self.id, self.signature)


class Annotation(Base):
  """Annotations of the GBU database consists only of the left and right eye positions.
  There is exactly one annotation for each file."""
  __tablename__ = 'annotation'

  id = Column(Integer, primary_key=True)
  file_id = Column(String(9), ForeignKey('file.id'))

  le_x = Column(Integer) # left eye
  le_y = Column(Integer)
  re_x = Column(Integer) # right eye
  re_y = Column(Integer)

  def __init__(self, presentation, eyes):
    self.file_id = presentation

    assert len(eyes) == 4
    self.re_x = int(eyes[0])
    self.re_y = int(eyes[1])
    self.le_x = int(eyes[2])
    self.le_y = int(eyes[3])

  def __repr__(self):
    return "<Annotation('%s': 'reye'=%dx%d, 'leye'=%dx%d)>" % (self.file_id, self.re_y, self.re_x, self.le_y, self.le_x)


class File(Base):
  """The file of the GBU database consists of an integral id
  as well as the 'presentation' as read from the file lists.
  Each file has one annotation and one associated client."""
  __tablename__ = 'file'

  id = Column(Integer, primary_key=True)
  client_id = Column(Integer, ForeignKey('client.id')) # The client id; should start with nd1
  path = Column(String(100), unique=True) # The relative path where to find the file

  presentation = Column(String(9), unique=True) # The signature of the file; should start with nd2
  client = relationship("Client", backref=backref("files", order_by=id))
  # one-to-one relationship between annotations and files
  annotation = relationship("Annotation", backref=backref("file", order_by=id, uselist=False), uselist=False)

  def __init__(self, presentation, signature, path):
    self.presentation = presentation
    self.client_id = client_id_from_signature(signature)
    self.path = path
    # signature is not stored, but needed for creation
    self.signature = signature

  def __repr__(self):
    return "<File('%s': %s , %d)>" % (self.presentation, self.path, self.client_id)

  def make_path(self, directory=None, extension=None):
    """Wraps the current path so that a complete path is formed

    Keyword parameters:

    directory
      An optional directory name that will be prefixed to the returned result.

    extension
      An optional extension that will be suffixed to the returned filename. The
      extension normally includes the leading ``.`` character as in ``.jpg`` or
      ``.hdf5``.

    Returns a string containing the newly generated file path.
    """
    if not directory: directory = ''
    if not extension: extension = ''

    return os.path.join(directory, self.path + extension)

  def save(self, data, directory=None, extension='.hdf5'):
    """Saves the input data at the specified location and using the given
    extension.

    Keyword parameters:

    data
      The data blob to be saved (normally a :py:class:`numpy.ndarray`).

    directory
      If not empty or None, this directory is prefixed to the final file
      destination

    extension
      The extension of the filename - this will control the type of output and
      the codec for saving the input blob.
    """
    path = self.make_path(directory, extension)
    bob.utils.makedirs_safe(os.path.dirname(path))
    bob.io.save(data, path)


# The subworld file association table is used as a many-to-many relationship between files and sub-worlds.
subworld_file_association = Table('subworld_file_association', Base.metadata,
  Column('subworld_id', Integer, ForeignKey('subworld.id')),
  Column('file_id',  Integer, ForeignKey('file.id')))

class Subworld(Base):
  """The subworld class defines different training set sizes.
  It is created from the 'x1', 'x2', 'x4' and 'x8' training lists from the GBU database."""
  __tablename__ = 'subworld'

  subworld_choices = ('x1', 'x2', 'x4', 'x8')

  id = Column(Integer, primary_key=True)
  name = Column(Enum(*subworld_choices))

  # back-reference from the file to the subworlds
  files = relationship("File", secondary=subworld_file_association, backref=backref("subworlds", order_by=id))

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    return "<Subworld('%s')>" % (self.name)


# The protocol file association table is used as a many-to-many relationship between files and protocols.
# Though I am not sure if files are actually shared between protocols...
protocol_file_association = Table('protocol_file_association', Base.metadata,
  Column('protocol_id', Integer, ForeignKey('protocol.id')),
  Column('file_id',  Integer, ForeignKey('file.id')))

class Protocol(Base):
  """The protocol class stores both the protocol name,
  as well as the purpose."""
  __tablename__ = 'protocol'

  protocol_choices = ('Good', 'Bad', 'Ugly')
  purpose_choices = ('enrol', 'probe')

  id = Column(Integer, primary_key=True)
  name = Column(Enum(*protocol_choices)) # one of the protocol names
  purpose = Column(Enum(*purpose_choices)) # one o the choices, enrol or probe

  # A direct link to the File objects associated with this Protocol
  files = relationship("File", secondary=protocol_file_association, backref=backref("protocols", order_by=id))

  def __init__(self, name, purpose):
    self.name = name
    self.purpose = purpose

  def __repr__(self):
    return "<Protocol('%s', '%s')>" % (self.name, self.purpose)
