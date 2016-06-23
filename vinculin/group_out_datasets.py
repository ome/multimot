"""\
Workaround for https://trello.com/c/qavXsAgD/158-miasreader-error
"""

import os
import errno

D = "/multimot/filesets/vinculin/20140110Dataset/TV 30 sec PAD output 20140110"
OUT_TAGS = ["DynOverlay", "Overlay", "mosaic", "patch_label", "roi_label"]

for name in os.listdir(D):
    if os.path.isdir(os.path.join(D, name)):
        print "doing:", name
        res_dir = os.path.join(D, name, "Sample1", "results")
        for tag in OUT_TAGS:
            basenames = [_ for _ in os.listdir(res_dir)
                         if _.endswith("_%s.tif" % tag)]
            dest_dir = os.path.join(D, name, "Sample1", tag)
            try:
                os.makedirs(dest_dir)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    pass
            for bn in basenames:
                source = os.path.join(res_dir, bn)
                link_name = os.path.join(dest_dir, bn)
                try:
                    os.symlink(source, link_name)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        pass

# update .screen files
for tag in OUT_TAGS:
    fn = os.path.join("screens", "%s.screen" % tag)
    with open(fn) as f:
        lines = [_ for _ in f]
    with open(fn, "w") as f:
        for l in lines:
            if l.startswith("Field_"):
                l = l.replace("/results", "/%s" % tag)
            f.write(l)
