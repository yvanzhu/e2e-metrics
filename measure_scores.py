#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import json
from argparse import ArgumentParser
from tempfile import mkdtemp
import os
import shutil
import subprocess
import re
import sys

from pycocotools.coco import COCO
from pycocoevalcap.eval import COCOEvalCap


def read_lines(file_name, multi_ref=False):
    """Read one instance per line from a text file. In multi-ref mode, assumes multiple lines
    (references) per instance & instances separated by empty lines."""
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


def read_and_check_tsv(sys_file, src_file):
    # read
    src_data = read_lines(src_file)
    sys_data = read_lines(sys_file)
    sys_data[0] = re.sub(u'\ufeff', '', sys_data[0])  # remove unicode BOM
    sys_data = [line.replace(u'Ł', u'£') for line in sys_data]  # fix Ł
    sys_data = [line.replace(u'Â£', u'£') for line in sys_data]  # fix Â£
    sys_data = [line.replace(u'Ã©', u'é') for line in sys_data]  # fix Ã©
    sys_data = [line.replace(u'ã©', u'é') for line in sys_data]  # fix ã©
    sys_data = [line.split("\t") for line in sys_data if line]  # split, ignore empty lines
    if len([line for line in sys_data if len(line) == 1]) == len(sys_data):  # split CSV
        sys_data = [line[0].split('","') for line in sys_data]

    if re.match(r'^"?mr', sys_data[0][0], re.I):  # ignore header
        sys_data = sys_data[1:]

    # check integrity
    if len(sys_data) != len(src_data):
        print "%s -- wrong data length" % sys_file
        raise ValueError('%s -- SYS data of different length than SRC: %d' % (sys_file, len(sys_data)))
    errs = [line_no for line_no, item in enumerate(sys_data, start=1) if len(item) != 2]
    if errs:
        print "%s -- weird number of values" % sys_file
        raise ValueError('%s -- Weird number of values on lines: %s' % (sys_file, str(errs)))

    # remove quotes
    sys_srcs = []
    sys_outs = []
    for sys_src, sys_out in sys_data:
        sys_src = re.sub(r'^\s*[\'"]?\s*', r'', sys_src)
        sys_src = re.sub(r'\s*[\'"]?\s*$', r'', sys_src)
        sys_out = re.sub(r'^\s*[\'"]?\s*', r'', sys_out)
        sys_out = re.sub(r'\s*[\'"]?\s*$', r'', sys_out)
        sys_srcs.append(sys_src)
        sys_outs.append(sys_out)

    # check sameness
    errs = [line_no for line_no, (sys, ref) in enumerate(zip(sys_srcs, src_data), start=1)
            if sys != ref]
    if errs:
        print "%s -- SRC fields not the same as reference" % sys_file
        raise ValueError('%s -- The SRC fields in SYS data are not the same as reference SRC on lines: %s' % (sys_file, str(errs)))
    # check quotes
    errs = [line_no for line_no, sys in enumerate(sys_outs, start=1) if '"' in sys]
    if errs:
        print "%s -- has quotes" % sys_file
        raise ValueError('%s -- Quotes on lines: %s' % (sys_file, str(errs)))

    # return the checked data
    return sys_outs


def create_coco_refs(data_ref):
    """Create MS-COCO human references JSON."""
    out = {'info': {}, 'licenses': [], 'images': [], 'type': 'captions', 'annotations': []}
    ref_id = 0
    for inst_id, refs in enumerate(data_ref):
        out['images'].append({'id': 'inst-%d' % inst_id})
        for ref in refs:
            out['annotations'].append({'image_id': 'inst-%d' % inst_id,
                                       'id': ref_id,
                                       'caption': ref})
            ref_id += 1
    return out


def create_coco_sys(data_sys):
    """Create MS-COCO system outputs JSON."""
    out = []
    for inst_id, inst in enumerate(data_sys):
        out.append({'image_id': 'inst-%d' % inst_id, 'caption': inst})
    return out


def create_mteval_file(refs, path, file_type):
    """Given references/outputs, create a MTEval .sgm XML file.
    @param refs: data to store in the file (human references/system outputs/dummy sources)
    @param path: target path where the file will be stored
    @param file_type: the indicated "set type" (ref/tst/src)
    """
    # swap axes of multi-ref data (to 1st: different refs, 2nd: instances) & pad empty references
    data = [[]]
    for inst_no, inst in enumerate(refs):
        if not isinstance(inst, list):  # single-ref data
            inst = [inst]
        for ref_no, ref in enumerate(inst):
            if len(data) <= ref_no:  # there's more refs than previously known: pad with empty
                data.append([''] * inst_no)
            data[ref_no].append(ref)
        ref_no += 1
        while ref_no < len(data):  # less references than previously: pad with empty
            data[ref_no].append('')
            ref_no += 1

    with codecs.open(path, 'wb', 'UTF-8') as fh:
        settype = file_type + 'set'
        fh.write('<%s setid="%s" srclang="any" trglang="%s">\n' % (settype, 'e2e', 'en'))
        for inst_set_no, inst_set in enumerate(data):
            sysid = file_type + ('' if len(data) == 1 else '_%d' % inst_set_no)
            fh.write('<doc docid="test" genre="news" origlang="any" sysid="%s">\n<p>\n' % sysid)
            for inst_no, inst in enumerate(inst_set, start=1):
                fh.write('<seg id="%d">%s</seg>\n' % (inst_no, inst))
            fh.write('</p>\n</doc>\n')
        fh.write('</%s>' % settype)


def evaluate(ref_file, sys_file, src_file=None, print_as_table=False, print_table_header=False):
    """Main procedure, running the MS-COCO & MTEval evaluators on the given files."""

    # read input files
    if src_file:
        data_sys = read_and_check_tsv(sys_file, src_file)
    else:
        data_sys = read_lines(sys_file)
    data_ref = read_lines(ref_file, multi_ref=True)
    # dummy source files (have no effect on measures, but MTEval wants them)
    data_src = [''] * len(data_sys)

    # create temp directory
    temp_path = mkdtemp(prefix='e2e-eval-')
    print >> sys.stderr, 'Creating temp directory ', temp_path

    # convert references to MS-COCO format in-memory
    coco_ref = create_coco_refs(data_ref)
    # create COCO test file (in a temporary file)
    coco_sys = create_coco_sys(data_sys)
    coco_sys_file = os.path.join(temp_path, 'coco_sys.json')
    with open(coco_sys_file, 'wb') as coco_sys_fh:
        json.dump(coco_sys, coco_sys_fh)

    # run the MS-COCO evaluator
    print >> sys.stderr, 'Running MS-COCO evaluator...'
    coco = COCO()
    coco.dataset = coco_ref
    coco.createIndex()

    coco_res = coco.loadRes(coco_sys_file)
    coco_eval = COCOEvalCap(coco, coco_res)
    coco_eval.evaluate()
    scores = {metric: score for metric, score in coco_eval.eval.items()}

    # create MTEval files
    mteval_ref_file = os.path.join(temp_path, 'mteval_ref.sgm')
    create_mteval_file(data_ref, mteval_ref_file, 'ref')
    mteval_sys_file = os.path.join(temp_path, 'mteval_sys.sgm')
    create_mteval_file(data_sys, mteval_sys_file, 'tst')
    mteval_src_file = os.path.join(temp_path, 'mteval_src.sgm')
    create_mteval_file(data_src, mteval_src_file, 'src')
    mteval_log_file = os.path.join(temp_path, 'mteval_log.txt')

    # run MTEval
    print >> sys.stderr, 'Running MTEval to compute BLEU & NIST...'
    mteval_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'mteval', 'mteval-v13a-sig.pl')
    mteval_out = subprocess.check_output(['perl', mteval_path,
                                          '-r', mteval_ref_file,
                                          '-s', mteval_src_file,
                                          '-t', mteval_sys_file,
                                          '-f', mteval_log_file], stderr=subprocess.STDOUT)
    scores['NIST'] = float(re.search(r'NIST score = ([0-9.]+)', mteval_out).group(1))
    scores['BLEU'] = float(re.search(r'BLEU score = ([0-9.]+)', mteval_out).group(1))
    print >> sys.stderr, mteval_out

    # print out the results
    metric_names = ['BLEU', 'NIST', 'METEOR', 'ROUGE_L', 'CIDEr']
    if print_as_table:
        if print_table_header:
            print '\t'.join(['File'] + metric_names)
        print '\t'.join([sys_file] + ['%.4f' % scores[metric] for metric in metric_names])
    else:
        print 'SCORES:\n=============='
        for metric in metric_names:
            print '%s: %.4f' % (metric, scores[metric])
        print

    # delete the temporary directory
    print >> sys.stderr, 'Removing temp directory'
    shutil.rmtree(temp_path)


if __name__ == '__main__':
    ap = ArgumentParser(description='E2E Challenge evaluation -- MS-COCO & MTEval wrapper')
    ap.add_argument('-s', '--src_file', type=str, help='source file -- if given, system output ' +
                    'should be a TSV with source & output columns, source is checked for integrity',
                    default=None)
    ap.add_argument('-t', '--table', action='store_true', help='print out results as a line in a table')
    ap.add_argument('-H', '--header', action='store_true', help='print table header')
    ap.add_argument('ref_file', type=str, help='references file -- multiple references separated by empty lines')
    ap.add_argument('sys_file', type=str, help='system output file to evaluate')
    args = ap.parse_args()

    evaluate(args.ref_file, args.sys_file, args.src_file, args.table, args.header)
