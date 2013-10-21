#!/usr/bin/env python

import os, sys
import re
import tempfile
import logging
from LogFile import LogFile
import shutil
from GtApp import GtApp
from pySimbad import pySimbad
from task import *

from optparse import Option
from optparse import OptionParser

usage = "usage: %prog [options] <ft1file> [ <ft1file> ... ]"
description = "Select a subset of the data"
parser = OptionParser(usage=usage,description=description)

parser.add_option('--dcostheta', default = 0.025, type='float',
                  help = '')

parser.add_option('--binsz', default = 1.0, type='float',
                  help = '')

parser.add_option('--zmax', default = 105.0, type='float',
                  help = 'Set the maximum zenith angle.')

parser.add_option('--output', default = None, type='string',
                  help = 'Output file')

parser.add_option('--scfile', default = None, type='string',
                  help = 'Output file')

parser.add_option("-l", "--logdir", dest="logdir", default=".", 
                  help="log DIRECTORY (default ./)")

parser.add_option("-v", "--loglevel", dest="loglevel", default="debug", 
                  help="logging level (debug, info, error)")

parser.add_option("-q", "--quiet", action="store_true", dest="quiet", 
                  help="do not log to console")

#parser.add_option("-c", "--clean", dest="clean", action="store_true", 
#                  default=False, help="remove old log file")

parser.add_option("--batch",action="store_true",
                  help="Split this job into several batch jobs.")

parser.add_option('--queue', default = None,
                  type='string',help='Set the batch queue.')

(opts, args) = parser.parse_args()

if len(args) < 1:
    parser.error("Incorrect number of arguments.")

if opts.scfile is None:
    raise Exception("No Spacecraft File")
    
scfile = os.path.abspath(opts.scfile)


if opts.batch:

    for x in args:
        cmd = 'gtltcube.py %s '%(x)
        
        for k, v in opts.__dict__.iteritems():
            if not v is None and k != 'batch': cmd += ' --%s=%s '%(k,v)

        print 'bsub -q %s -R rhel60 %s'%(opts.queue,cmd)
        os.system('bsub -q %s -R rhel60 %s'%(opts.queue,cmd))

    sys.exit(0)


for f in args:

    f = os.path.abspath(f)
    
    if opts.output is None:

        m = re.search('(.+)_ft1(.*)\.fits?',f)
        if not m is None:
            outfile = m.group(1) + '_gtltcube.fits'
        else:
            outfile = os.path.splitext(f)[0] + '_gtltcube.fits'
    else:
        outfile = opts.output

    gt_task = LTCubeTask(outfile,
                         dcostheta=opts.dcostheta,
                         binsz=opts.binsz,
                         zmax=opts.zmax,
                         evfile=f,
                         scfile=scfile)

    gt_task.run()
    

sys.exit(0)

files = []
for i in range(1,len(args)):
    files.append(os.path.abspath(args[i]))

cwd = os.getcwd()
user = os.environ['USER']
tmpdir = tempfile.mkdtemp(prefix=user + '.', dir='/scratch')

os.chdir(tmpdir)


fd, file_list = tempfile.mkstemp(dir=tmpdir)
for file in files:
    os.write(fd,file + '\n')

sys.stdout = LogFile('stdout','gtltcube.log',quiet=False)
sys.stderr = LogFile('stderr','gtltcube.log',quiet=False)

ltcube = GtApp('gtltcube', 'Likelihood')

file_prefix = opts.output

outfile = file_prefix + '_gtltcube.fits'
logfile = file_prefix + '_gtltcube.log'

ltcube['dcostheta'] = opts.dcostheta
ltcube['binsz'] = opts.binsize
ltcube['outfile'] = outfile
ltcube['evfile'] = '@' + file_list
ltcube['scfile'] = scfile
ltcube['zmax'] = opts.zmax

try:
    ltcube.run()
except:
    print logging.getLogger('stderr').exception(sys.exc_info()[0])

os.system('mv gtltcube.log ' + cwd + '/' + logfile)
os.system('mv ' + outfile + ' ' + cwd)

shutil.rmtree(tmpdir)





