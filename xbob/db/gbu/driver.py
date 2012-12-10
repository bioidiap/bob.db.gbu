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

"""Commands the GBU database can respond to.
"""

import os
import sys
import tempfile, shutil
import argparse

from bob.db import utils
from bob.db.driver import Interface as BaseInterface

def dumplist(args):
  """Dumps lists of files based on your criteria"""

  from .query import Database
  db = Database()

  r = db.objects(
      groups=args.group,
      subworld=args.subworld,
      protocol=args.protocol,
      purposes=args.purpose
  )

  output = sys.stdout
  if args.selftest:
    output = utils.null()

  for file in r:
    output.write('%s\n' % file.make_path(args.directory, args.extension))

  return 0

def checkfiles(args):
  """Checks existence of files based on your criteria"""

  from .query import Database
  db = Database()

  objects = db.objects()

  # go through all files, check if they are available on the filesystem
  good = {}
  bad = {}
  for file in objects:
    if os.path.exists(file.make_path(args.directory, args.extension)):
      good[file.id] = file
    else:
      bad[file.id] = file

  # report
  output = sys.stdout
  if args.selftest:
    output = utils.null()

  if bad:
    for id, file in bad.items():
      output.write('Cannot find file "%s"\n' % (file.make_path(args.directory, args.extension),))
    output.write('%d files (out of %d) were not found at "%s"\n' % \
        (len(bad), len(objects), args.directory))

  return 0


def copy_image_files(args):
  """This function scans the given input directory for the images
  required by this database and creates a new directory with the
  required sub-directory structure, by copying or linking the images"""

  if os.path.exists(args.new_image_directory):
    print "Directory", args.new_image_directory, "already exists, please choose another one."
    return
  # collect the files in the given directory
  from .create import collect_files
  print "Collecting image files from directory", args.original_image_directory
  filelist, dirlist = collect_files(args.original_image_directory, args.original_image_extension, args.sub_directory)

  print "Done. Found", len(filelist), "image files."
  # get the files of the database
  from .query import Database
  db = Database()
  db_files = db.objects()

  # create a temporary structure for faster access
  temp_dict = {}
  for file in db_files:
    temp_dict[os.path.basename(file.path)[0]] = file

  command = os.symlink if args.soft_link else shutil.copy
  print "Copying (or linking) files to directory", args.new_image_directory
  # now, iterate through the detected files
  for index in range(len(filelist)):
    file_wo_extension = os.path.splitext(filelist[index])[0]
    if file_wo_extension in temp_dict:
      # get the files
      old_file = os.path.join(args.original_image_directory, dirlist[index], filelist[index])
      new_file = temp_dict[file_wo_extension].make_path(args.new_image_directory, '.jpg')
      new_dir = os.path.dirname(new_file)
      if not os.path.exists(new_dir):
        os.makedirs(new_dir)

      # copy or link
      assert not os.path.exists(new_file)
      command(old_file, new_file)

  return 0


def create_annotation_files(args):
  """Creates the eye position files for the GBU database
  (using the eye positions stored in the database),
  so that GBU shares the same structure as other databases.

  This function is deprecated, please do not use it anymore.
  """

  print >> sys.stderr, "Warning: this function is deprecated. Please use the Database.annotations() function to get the annotations."

  # report
  output = sys.stdout
  if args.selftest:
    output = utils.null()
    args.directory = tempfile.mkdtemp(prefix='xbob_db_gbu_')

  from .query import Database
  db = Database()

  # retrieve all files
  files = db.objects()
  for file in files:
    filename = file.make_path(directory=args.directory, extension=args.extension)
    if not os.path.exists(os.path.dirname(filename)):
      os.makedirs(os.path.dirname(filename))
    eyes = db.annotations(file.id)
    f = open(filename, 'w')
    # write eyes in with annotations: right eye, left eye
    f.writelines('reye' + ' ' + str(eyes['reye'][1]) + ' ' + str(eyes['reye'][0]) + '\n')
    f.writelines('leye' + ' ' + str(eyes['leye'][1]) + ' ' + str(eyes['leye'][0]) + '\n')
    f.close()


  if args.selftest:
    # check that all files really exist
    args.selftest = False
    args.groups = None
    args.subworld = None
    args.protocol = None
    args.purposes = None
    checkfiles(args)
    shutil.rmtree(args.directory)

  return 0



class Interface(BaseInterface):

  def name(self):
    return 'gbu'

  def version(self):
    import pkg_resources  # part of setuptools
    return pkg_resources.require('xbob.db.%s' % self.name())[0].version

  def files(self):
    from pkg_resources import resource_filename
    raw_files = ('db.sql3',)
    return [resource_filename(__name__, k) for k in raw_files]

  def type(self):
    return 'sqlite'

  def add_commands(self, parser):
    from . import __doc__ as docs

    subparsers = self.setup_parser(parser,
       "The GBU database", docs)

    # get the "create" action from a submodule
    from .create import add_command as create_command
    create_command(subparsers)

    from .models import Protocol, Subworld

    # the "dumplist" action
    dump_list_parser = subparsers.add_parser('dumplist', help=dumplist.__doc__)
    dump_list_parser.add_argument('-d', '--directory', help="if given, this path will be prepended to every entry returned.")
    dump_list_parser.add_argument('-e', '--extension', help="if given, this extension will be appended to every entry returned.")
    dump_list_parser.add_argument('-g', '--group', help="if given, this value will limit the output files to those belonging to a particular group.", choices=('world', 'dev'))
    dump_list_parser.add_argument('-s', '--subworld', help="if given, limits the dump to a particular subworld of the data.", choices=Subworld.subworld_choices)
    dump_list_parser.add_argument('-p', '--protocol', help="if given, limits the dump to a particular subset of the data that corresponds to the given protocol.", choices=Protocol.protocol_choices)
    dump_list_parser.add_argument('-u', '--purpose', help="if given, this value will limit the output files to those designed for the given purposes.", choices=Protocol.purpose_choices)
    dump_list_parser.add_argument('--self-test', dest="selftest", action='store_true', help=argparse.SUPPRESS)
    dump_list_parser.set_defaults(func=dumplist) #action

    # the "checkfiles" action
    check_files_parser = subparsers.add_parser('checkfiles', help=checkfiles.__doc__)
    check_files_parser.add_argument('-d', '--directory', help="if given, this path will be prepended to every entry returned.")
    check_files_parser.add_argument('-e', '--extension', help="if given, this extension will be appended to every entry returned.")
    check_files_parser.add_argument('--self-test', dest="selftest", action='store_true', help=argparse.SUPPRESS)

    check_files_parser.set_defaults(func=checkfiles) #action

    # the "copy-image-files" action
    copy_image_files_parser = subparsers.add_parser('copy-image-files', help=copy_image_files.__doc__)
    copy_image_files_parser.add_argument('-d', '--original-image-directory', metavar='DIR', required=True, help="Specify the image directory containing the MBGC-V1 images.")
    copy_image_files_parser.add_argument('-e', '--original-image-extension', metavar='EXT', default = '.jpg', help="The extension of the images in the database.")
    copy_image_files_parser.add_argument('-n', '--new-image-directory', metavar='DIR', required=True, help="Specify the image directory where the images should be copied to.")
    copy_image_files_parser.add_argument('-s', '--sub-directory', metavar='DIR', help="To speed up the search process you might define a sub-directory that is scanned, e.g., 'Original'.")
    copy_image_files_parser.add_argument('-l', '--soft-link', action='store_true', help="If selected, the images will be linked rather than copied.")
    copy_image_files_parser.set_defaults(func=copy_image_files) #action

    # the (deprecated) "create-eye-files" action
    create_annotation_files_parser = subparsers.add_parser('create-annotation-files', help=create_annotation_files.__doc__)
    create_annotation_files_parser.add_argument('-d', '--directory', required=True, help="The eye position files will be stored in this directory")
    create_annotation_files_parser.add_argument('-e', '--extension', default = '.pos', help="if given, this extension will be appended to every entry returned.")
    create_annotation_files_parser.add_argument('--self-test', dest="selftest", action='store_true', help=argparse.SUPPRESS)
    create_annotation_files_parser.set_defaults(func=create_annotation_files) #action


