#!/usr/bin/env python

import sys
import os
import re
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

PATTERNS = [
    # top-level: unprocessed cell movies (greyscale, separate
    # channels). Channel tags are 1, 2, 3.
    re.compile(r"^(.+)t(?P<t>\d+)(.+)c([123]).tif$"),
    # "*/BilatFilteredNonStand/": bilateral filtered data (greyscale,
    # separate channels). Channel tags are C, Y, P. There's also a CY
    # channel, but it's computed from C and Y (mean value).
    re.compile(r"^(.+)([CYP])(.+)t(?P<t>\d+)(.+)$"),
]


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


def get_pattern(subdir, level=0):
    fnames = [_ for _ in os.listdir(subdir) if _.endswith(".tif")]
    if level == 1:
        fnames = [_ for _ in fnames if not _.startswith("bilaf_CY")]
    all_groups, t_indices = [], []
    for fn in fnames:
        try:
            p = PATTERNS[level]
        except IndexError:
            raise ValueError("Unsupported level: %d" % level)
        m = p.match(fn)
        if m is None:
            sys.stderr.write("WARNING: %s: unexpected pattern\n" % fn)
        else:
            t_indices.append(m.groupdict()["t"])
            all_groups.append(m.groups())
    fixed = all_groups[0][::2]
    for g in all_groups:
        assert g[::2] == fixed
    # check for fixed-width
    assert len(set(map(len, t_indices))) == 1
    t_block = "t<%s-%s>" % (min(t_indices), max(t_indices))
    if level == 0:
        return "".join([fixed[0], t_block, fixed[1], "c<1-3>", ".tif"])
    elif level == 1:
        return "".join([fixed[0], "<C,Y,P>", fixed[1], t_block, fixed[2]])


def write_screen(data_dir, plate, outf, screen=None, level=0):
    kwargs = {"screen_name": screen} if screen else {}
    writer = ScreenWriter(plate, ROWS, COLUMNS, FIELDS, **kwargs)
    subd_map = get_subdir_mapping(data_dir)
    extra_kv = {"AxisTypes": "CT"} if level == 1 else None
    for idx in xrange(ROWS * COLUMNS):
        field_values = []
        try:
            subdir = os.path.join(data_dir, subd_map[idx])
        except KeyError:
            pass
        else:
            if level == 1:
                subdir = os.path.join(subdir, "BilatFilteredNonStand")
            for run in xrange(FIELDS):
                pattern = get_pattern(subdir, level=level)
                field_values.append(os.path.join(subdir, pattern))
        writer.add_well(field_values, extra_kv=extra_kv)
    writer.write(outf)


def parse_cl(argv):
    parser = ArgumentParser()
    parser.add_argument("dir", metavar="DIR", help="dir")
    parser.add_argument("-o", "--output", metavar="FILE", help="output file")
    parser.add_argument("-p", "--plate", metavar="PLATE", help="plate name")
    parser.add_argument("-s", "--screen", metavar="SCREEN", help="screen name")
    parser.add_argument("-l", "--level", metavar="INT", type=int, default=0,
                        help="subdirectory level")
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_cl(argv)
    if args.output:
        outf = open(args.output, "w")
        print "writing to %s" % args.output
    else:
        outf = sys.stdout
    write_screen(
        args.dir, args.plate, outf, screen=args.screen, level=args.level
    )
    if outf is not sys.stdout:
        outf.close()


if __name__ == "__main__":
    main(sys.argv)
