#!/usr/bin/env python

import sys
import os
import errno
import csv
from argparse import ArgumentParser


def mkdir_p(d):
    try:
        os.makedirs(d)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass


def parse_cl(argv):
    parser = ArgumentParser()
    parser.add_argument("dir", metavar="DIR", help="dir")
    parser.add_argument("-o", "--out-dir", metavar="DIR", help="output dir")
    return parser.parse_args(argv[1:])


def get_table_fnames(top_dir):
    table_fnames = {}
    for name in os.listdir(top_dir):
        subd = os.path.join(top_dir, name)
        if os.path.isdir(subd):
            tfn = os.path.join(subd, "Sample1", "results",
                               "PADtrack_0001_z000_f000_ROIReport.txt")
            assert os.path.exists(tfn)
            table_fnames[name] = tfn
    return table_fnames


def adapt_table(fn, out_fn):
    """
    Adapts the table for the current version of OMERO's metadata plugin.

    More specifically: replaces empty values with NaNs; removes empty
    columns; adds column types; converts to comma-separated.

    TODO: look at the whole column (instead of just at the first value)
    to decide on type assignment or removal.
    """
    with open(fn) as fi, open(out_fn, "w") as fo:
        reader = csv.DictReader(fi, delimiter="\t")
        sample = reader.next()
        fi.seek(0)
        in_header = fi.next().strip().split("\t")
        out_header = [_ for _ in in_header if sample[_].strip()]
        type_codes = []
        for k in out_header:
            v = sample[k]
            try:
                int(v)
                type_codes.append('l')
            except ValueError:
                try:
                    float(v)
                    type_codes.append('d')
                except ValueError:
                    type_codes.append('s')
        fo.write("# header %s\n" % ",".join(type_codes))
        writer = csv.DictWriter(fo, out_header, delimiter=",",
                                extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            for k in row:
                if not(row[k].strip()):
                    row[k] = "nan"
            writer.writerow(row)


def main(argv):
    args = parse_cl(argv)
    if args.out_dir:
        mkdir_p(args.out_dir)
    else:
        args.out_dir = os.getcwd()
    for name, fn in get_table_fnames(args.dir).iteritems():
        subd = os.path.join(args.out_dir, name)
        mkdir_p(subd)
        out_fn = os.path.join(subd, os.path.basename(fn))
        adapt_table(fn, out_fn)


if __name__ == "__main__":
    main(sys.argv)
