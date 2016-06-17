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
    # "*/BilatFilteredNonStand/RatioIm/": RGB movies
    re.compile(r"^(.+)t(?P<t>\d+)(.+)$"),
]

SINGLE_C = re.compile(r"^(.+)t(?P<t>\d+)(.+)$")
MULTI_C = re.compile(r"^(.+)([123])(.+)t(?P<t>\d+)(.+)$")
OUT_PATTERNS = {
    "0001": MULTI_C,
    "Overlay": MULTI_C,
    "DynOverlay": SINGLE_C,
    "mosaic": MULTI_C,
    "patch_label": SINGLE_C,
    "roi_label": SINGLE_C,
}
DEFAULT_TAG = "0001"


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


def get_block_info(fnames, re_pattern):
    """
    All filename patterns have fixed (i.e., that do not change from
    one file to another) and variable blocks. One of the variable
    blocks is always a T block, and the number of time points depends
    on the subdir.
    """
    all_groups, t_indices = [], []
    for fn in fnames:
        m = re_pattern.match(fn)
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
    return t_block, fixed


def get_pattern(subdir, level=0):
    try:
        p = PATTERNS[level]
    except IndexError:
        raise ValueError("Unsupported level: %d" % level)
    fnames = [_ for _ in os.listdir(subdir) if _.endswith(".tif")]
    if level == 1:
        fnames = [_ for _ in fnames if not _.startswith("bilaf_CY")]
    t_block, fixed = get_block_info(fnames, p)
    if level == 0:
        return "".join([fixed[0], t_block, fixed[1], "c<1-3>", ".tif"])
    elif level == 1:
        return "".join([fixed[0], "<C,Y,P>", fixed[1], t_block, fixed[2]])
    elif level == 2:
        return "".join([fixed[0], t_block, fixed[1]])


def get_out_pattern(subdir, tag):
    try:
        p = OUT_PATTERNS[tag]
    except KeyError:
        raise ValueError("Unknown output tag: %s" % tag)
    fnames = [_ for _ in os.listdir(subdir) if _.endswith(".tif")]
    if tag != "0001":
        fnames = [_ for _ in fnames
                  if os.path.splitext(_)[0].endswith("_" + tag)]
    t_block, fixed = get_block_info(fnames, p)
    if p is SINGLE_C:
        return "".join([fixed[0], t_block, fixed[1]])
    else:
        assert p is MULTI_C
        return "".join([fixed[0], "<1-3>", fixed[1], t_block, fixed[2]])


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
            if level > 0:
                subdir = os.path.join(subdir, "BilatFilteredNonStand")
            if level > 1:
                subdir = os.path.join(subdir, "RatioIm")
            for run in xrange(FIELDS):
                pattern = get_pattern(subdir, level=level)
                field_values.append(os.path.join(subdir, pattern))
        writer.add_well(field_values, extra_kv=extra_kv)
    writer.write(outf)


def write_out_screen(data_dir, plate, outf, screen=None, tag=DEFAULT_TAG):
    kwargs = {"screen_name": screen} if screen else {}
    writer = ScreenWriter(plate, ROWS, COLUMNS, FIELDS, **kwargs)
    subd_map = get_subdir_mapping(data_dir)
    extra_kv = {"AxisTypes": "CT"}
    for idx in xrange(ROWS * COLUMNS):
        field_values = []
        try:
            subdir = os.path.join(data_dir, subd_map[idx], "Sample1")
        except KeyError:
            pass
        else:
            if tag == "0001":
                subdir = os.path.join(subdir, tag)
            else:
                subdir = os.path.join(subdir, "results")
            for run in xrange(FIELDS):
                pattern = get_out_pattern(subdir, tag)
                field_values.append(os.path.join(subdir, pattern))
        writer.add_well(field_values, extra_kv=extra_kv)
    writer.write(outf)


def parse_cl(argv):
    parser = ArgumentParser()
    parser.add_argument("dir", metavar="DIR", help="dir")
    parser.add_argument("-o", "--output", metavar="FILE", help="output file")
    parser.add_argument("-p", "--plate", metavar="PLATE", help="plate name")
    parser.add_argument("-s", "--screen", metavar="SCREEN", help="screen name")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-l", "--level", metavar="INT", type=int, default=0,
                   help="subdirectory level (input datasets)")
    g.add_argument("-t", "--tag", choices=sorted(OUT_PATTERNS),
                   metavar="|".join(sorted(OUT_PATTERNS)),
                   help="dataset tag (output datasets)")
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_cl(argv)
    if args.output:
        outf = open(args.output, "w")
        print "writing to %s" % args.output
    else:
        outf = sys.stdout
    if args.tag:
        write_out_screen(
            args.dir, args.plate, outf, screen=args.screen, tag=args.tag
        )
    else:
        write_screen(
            args.dir, args.plate, outf, screen=args.screen, level=args.level
        )
    if outf is not sys.stdout:
        outf.close()


if __name__ == "__main__":
    main(sys.argv)
