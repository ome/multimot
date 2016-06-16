#!/usr/bin/env python

import sys
import os
import re
from operator import itemgetter
from argparse import ArgumentParser

try:
    from pyidr.screenio import ScreenWriter
except ImportError:
    sys.exit("ERROR: this script requires pyidr, currently part of:\n"
             "https://github.com/openmicroscopy/idr-metadata")

# Although the paper mentions 96-wells plates, cells were imaged
# separately. Also, different cells can come from the same well. Here
# we map each cell to a well in a 96-well plate to aid visualization.
ROWS = 8
COLUMNS = 12
FIELDS = 1

FN_PATTERN = re.compile(r"^(.+)t(\d+)(.+)c(\d).tif$")


def get_subdir_mapping(data_dir):
    """
    Map cell IDs to subdirs. Trailing numeric IDs are in the 1-96
    range, so they can directly map to wells in our "virtual" plate.
    """
    subdirs = [_ for _ in os.listdir(data_dir)
               if os.path.isdir(os.path.join(data_dir, _))]
    cell_ids = [int(_.strip().rsplit(None, 1)[-1]) for _ in subdirs]
    assert len(set(cell_ids)) == len(subdirs)
    return dict(zip(cell_ids, subdirs))


def get_pattern(subdir):
    fnames = [_ for _ in os.listdir(subdir) if _.endswith(".tif")]
    all_groups = []
    for fn in fnames:
        try:
            all_groups.append(FN_PATTERN.match(fn).groups())
        except AttributeError:
            sys.stderr.write("WARNING: %s: unexpected pattern\n" % fn)
    start, mid = all_groups[0][0], all_groups[0][2]
    for g in all_groups:
        assert g[0] == start and g[2] == mid
    # numeric IDs are fixed-width, so we can just sort them as strings
    all_groups.sort(key=itemgetter(3))
    all_groups.sort(key=itemgetter(1))
    t_min, c_min = all_groups[0][1], all_groups[0][3]
    t_max, c_max = all_groups[-1][1], all_groups[-1][3]
    return "".join([start, "t<%s-%s>" % (t_min, t_max),
                    mid, "c<%s-%s>" % (c_min, c_max), ".tif"])


def write_screen(data_dir, plate, outf, screen=None):
    kwargs = {"screen_name": screen} if screen else {}
    writer = ScreenWriter(plate, ROWS, COLUMNS, FIELDS, **kwargs)
    subd_map = get_subdir_mapping(data_dir)
    for idx in xrange(ROWS * COLUMNS):
        field_values = []
        try:
            subdir = os.path.join(data_dir, subd_map[idx])
        except KeyError:
            pass
        else:
            for run in xrange(FIELDS):
                pattern = get_pattern(subdir)
                field_values.append(os.path.join(subdir, pattern))
        writer.add_well(field_values)
    writer.write(outf)


def parse_cl(argv):
    parser = ArgumentParser()
    parser.add_argument("dir", metavar="DIR", help="dir")
    parser.add_argument("-o", "--output", metavar="FILE", help="output file")
    parser.add_argument("-p", "--plate", metavar="PLATE", help="plate name")
    parser.add_argument("-s", "--screen", metavar="SCREEN", help="screen name")
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_cl(argv)
    if args.output:
        outf = open(args.output, "w")
        print "writing to %s" % args.output
    else:
        outf = sys.stdout
    write_screen(args.dir, args.plate, outf, screen=args.screen)
    if outf is not sys.stdout:
        outf.close()


if __name__ == "__main__":
    main(sys.argv)
