#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import json
from argparse import ArgumentParser
from tempfile import mkstemp
from pycocotools.coco import COCO
from pycocoevalcap.eval import COCOEvalCap
import os

def read_lines(file_name, multi_ref=False):
    buf = [[]] if multi_ref else []
    with codecs.open(file_name, 'rb', 'UTF-8') as fh:
        for line in fh:
            line = line.strip()
            if multi_ref:
                if not line:
                    buf.append([])
                else:
                    buf[-1].append(line)
            else:
                buf.append(line)
    if multi_ref and not buf[-1]:
        del buf[-1]
    return buf


def create_coco_refs(refs):
    out = {'info': {}, 'licenses': [], 'images': [], 'type': 'captions', 'annotations': []}
    ref_id = 0
    for inst_id, refs_ in enumerate(refs):
        out['images'].append({'id': 'inst-%d' % inst_id})
        for ref in refs_:
            out['annotations'].append({'image_id': 'inst-%d' % inst_id,
                                       'id': ref_id,
                                       'caption': ref})
            ref_id += 1
    return out


def create_coco_sys(sys):
    out = []
    for inst_id, inst in enumerate(sys):
        out.append({'image_id': 'inst-%d' % inst_id, 'caption': inst})
    return out


def evaluate(ref_file, sys_file):
    """Main procedure, running the COCO evaluator on the given files."""

    # create references in-memory
    refs = create_coco_refs(read_lines(ref_file, multi_ref=True))
    # create test file (in a temporary file)
    sys = create_coco_sys(read_lines(sys_file))
    _, sys_tmp_file = mkstemp(prefix='cocowrapper')
    with open(sys_tmp_file, 'wb') as sys_tmp_fh:
        json.dump(sys, sys_tmp_fh)

    # run the COCO evaluator
    coco = COCO()
    coco.dataset = refs
    coco.createIndex()

    coco_res = coco.loadRes(sys_tmp_file)
    coco_eval = COCOEvalCap(coco, coco_res)
    coco_eval.evaluate()

    print 'SCORES:\n=============='
    for metric, score in coco_eval.eval.items():
        print '%s: %.4f' % (metric, score)
    # delete the temporary file
    os.remove(sys_tmp_file)


if __name__ == '__main__':
    ap = ArgumentParser(description='MS-COCO Caption evaluator wrapper')
    ap.add_argument('ref_file', type=str, help='references file -- multiple references separated by empty lines')
    ap.add_argument('sys_file', type=str, help='system output file to evaluate')
    args = ap.parse_args()

    evaluate(args.ref_file, args.sys_file)
