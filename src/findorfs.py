#!python

import os, sys, string, time, BaseHTTPServer, getopt, re, subprocess, webbrowser
from operator import itemgetter

from utils import *
from assemble import Assemble

sys.path.append(INITIAL_UTILS)
from ruffus import *

_readlibs = []
_skipsteps = []
_asm = None
_settings = Settings()
_orf = None 

def init(reads, skipsteps, asm, orf):
   global _readlibs
   global _skipsteps
   global _asm
   global _orf
   _readlibs = reads
   _skipsteps = skipsteps
   _asm = asm
   _orf = orf

def parse_genemarkout(orf_file,is_scaff=False, error_stream="FindORFS"):
    coverageFile = open("%s/Assemble/out/%s.contig.cvg"%(_settings.rundir, _settings.PREFIX), 'r')
    cvg_dict = {} 
    for line in coverageFile:
        data = line.split()
        cvg_dict[data[0]] = float(data[1])
    coverageFile.close()

    coords = open(orf_file,'r')
    coords.readline()
#    outf = open("proba.orfs",'w')
    prevhdr = 0
    prevhdraa = 0
    prevhdrnt = 0

    curcontig = ""
    curseqaa = ""
    curseqnt = ""
    reads = {}
    gene_dict = {}
    fna_dict = {}
    for line in coords:
        if ">gene" in line[0:10]:
            if "_nt|" in line:
                #print prevhdraa, prevhdrnt#, curseqaa, curseqnt
                if prevhdraa and curseqaa != "":
                    try:
                        gene_dict[curcontig].append(curseqaa)
                    except KeyError:
                        gene_dict[curcontig] = []
                        gene_dict[curcontig].append(curseqaa)
                    curseqaa = ""

                elif prevhdrnt and curseqnt != "":
                    try:
                        fna_dict[curcontig].append(curseqnt)
                    except KeyError:
                        fna_dict[curcontig] = []
                        fna_dict[curcontig].append(curseqnt)
                    curseqnt = ""

                prevhdrnt = 1
                prevhdraa = 0

            elif "_aa|" in line:

                if prevhdrnt and curseqnt != "":
                    try:
                        fna_dict[curcontig].append(curseqnt)
                    except KeyError:
                        fna_dict[curcontig] = []
                        fna_dict[curcontig].append(curseqnt)
                    curseqnt = ""
                elif prevhdraa and curseqaa != "":
                    try:
                        gene_dict[curcontig].append(curseqaa)
                    except KeyError:
                        gene_dict[curcontig] = []
                        gene_dict[curcontig].append(curseqaa)
                    curseqaa = ""
                prevhdraa = 1
                prevhdrnt = 0

            prevhdr = 1
            lined = line.replace("\n","")
            data = line[1:].split(">",1)[1]
            
            curcontig = data.split(" ")[0]
            if len(data.split(" ")) == 1:
                curcontig = data.split("\t")[0]
            curcontig = curcontig.strip()
            #print curcontig, len(curcontig)
            prevhdr = 1

        elif len(line) > 2 and prevhdraa == 1 and prevhdr:
            curseqaa += line
        elif len(line) > 2 and prevhdrnt == 1 and prevhdr:
            curseqnt += line
        elif len(line) <= 2 or "Nucleotide" in line: #and prevhdr == 1:
            prevhdr = 0
            #prevhdraa = 0
            #prevhdrnt = 0

        else:
            continue
    if prevhdraa and curseqaa != "":
        try:
          gene_dict[curcontig].append(curseqaa)
        except KeyError:
          gene_dict[curcontig] = []
          gene_dict[curcontig].append(curseqaa)
          curseqaa = ""

    elif prevhdrnt and curseqnt != "":
        try:
          fna_dict[curcontig].append(curseqnt)
        except KeyError:
          fna_dict[curcontig] = []
          fna_dict[curcontig].append(curseqnt)
    if is_scaff:
        outf = open("%s/FindScaffoldORFS/out/%s.faa"%(_settings.rundir,_settings.PREFIX),'w')
        outf2 = open("%s/FindScaffoldORFS/out/%s.fna"%(_settings.rundir,_settings.PREFIX),'w')
        #cvgf = open("%s/FindScaffoldORFS/out/%s.contig.cvg"%(_settings.rundir,_settings.PREFIX),'w')
        cvgg = open("%s/FindScaffoldORFS/out/%s.gene.cvg"%(_settings.rundir,_settings.PREFIX),'w')
    else:
        outf = open("%s/FindORFS/out/%s.faa"%(_settings.rundir,_settings.PREFIX),'w')
        outf2 = open("%s/FindORFS/out/%s.fna"%(_settings.rundir,_settings.PREFIX),'w')
        #cvgf = open("%s/FindORFS/out/%s.contig.cvg"%(_settings.rundir,_settings.PREFIX),'w')
        cvgg = open("%s/FindORFS/out/%s.gene.cvg"%(_settings.rundir,_settings.PREFIX),'w')
    #print len(gene_dict.keys())
    orfs = {}

    for key in gene_dict.keys():
        genecnt = 1

        if not is_scaff:
            if key in cvg_dict.keys():
                cvgg.write("%s_gene%d\t%s\n"%(key,genecnt,cvg_dict[key])) 
            else:
                cvgg.write("%s_gene%d\t%s\n"%(key,genecnt, 1.0))
        for gene in gene_dict[key]:
            #min aa length, read depth
            if len(gene) < 100:# or cvg_dict[key] < 5:
                continue
            try:
                #print "contig"+key
                orfs["%s"%(key)] +=1
            except KeyError:
                orfs["%s"%(key)] =1
            outf.write(">%s_gene%d\n%s"%(key,genecnt,gene))

            genecnt +=1
    for key in fna_dict.keys():
        for gene in fna_dict[key]:
            if len(gene) < 300:# or cvg_dict[key] < 5:
                continue
            outf2.write(">%s_gene%d\n%s"%(key,genecnt,gene))
#        print gene_dict[key][0]
    outf.close()
    cvgg.close()

def parse_fraggenescanout(orf_file,is_scaff=False, error_stream="FindORFS"):
    coverageFile = open("%s/Assemble/out/%s.contig.cvg"%(_settings.rundir, _settings.PREFIX), 'r')
    cvg_dict = {} 

    for line in coverageFile:
        data = line.split()
        cvg_dict[data[0]] = float(data[1])
    coverageFile.close()
    genefile = ""
    if is_scaff:
        genefile = open("%s/FindScaffoldORFS/out/%s.orfs.ffn"%(_settings.rundir,_settings.PREFIX),'r')
        cvgg = open("%s/FindScaffoldORFS/out/%s.gene.cvg"%(_settings.rundir,_settings.PREFIX),'w')
    else:
        genefile = open("%s/FindORFS/out/%s.orfs.ffn"%(_settings.rundir,_settings.PREFIX),'r')
        cvgg = open("%s/FindORFS/out/%s.gene.cvg"%(_settings.rundir,_settings.PREFIX),'w')
    orfs = {}
  
    data = genefile.read()
    seqs = data.split(">")[1:]
    gene_ids = []    
    for seq in seqs:
        hdr,gene = seq.split("\n",1)
        hdr = hdr.split("\n")[0]
        gene_ids.append(hdr)
    for key in gene_ids:
        genecnt = 1
        gkey = ""
        if not is_scaff:
            for ckey in cvg_dict.keys():
                if ckey in key:
                    gkey = ckey
            
            if gkey != "":
                cvgg.write("%s\t%s\n"%(key,cvg_dict[gkey])) 
            else:
                cvgg.write("%s\t%s\n"%(key,1.0))
    cvgg.close()

@follows(Assemble)
@files("%s/Assemble/out/%s.asm.contig"%(_settings.rundir,_settings.PREFIX),"%s/FindORFS/out/%s.faa"%(_settings.rundir,_settings.PREFIX))
def FindORFS(input,output):
   if "FindORFS" in _skipsteps:
      run_process(_settings, "touch %s/FindRepeats/in/%s.fna"%(_settings.rundir, _settings.PREFIX),"FindORFS")
      run_process(_settings, "touch %s/FindORFS/out/%s.faa"%(_settings.rundir, _settings.PREFIX),"FindORFS")
      return 0

   if _asm == "soap":
         
       #if not os.path.exists("%s/Assemble/out/%s.asm.scafSeq.contigs"%(_settings.rundir,_settings.PREFIX)):
       #    run_process(_settings, "python %s/python/extract_soap_contigs.py %s/Assemble/out/%s.asm.scafSeq"%(_settings.METAMOS_UTILS,_settings.rundir,_settings.PREFIX))
       #run_process(_settings, "unlink %s/FindORFS/in/%s.asm.scafSeq.contigs"%(_settings.rundir,_settings.PREFIX))
       #run_process(_settings, "unlink %s/FindORFS/in/%s.asm.contig"%(_settings.rundir,_settings.PREFIX))
       #run_process(_settings, "ln -t %s/FindORFS/in/ -s %s/Assemble/out/%s.asm.scafSeq.contigs"%(_settings.rundir, _settings.rundir,_settings.PREFIX))
       #run_process(_settings, "cp %s/FindORFS/in/%s.asm.scafSeq.contigs  %s/FindORFS/in/%s.asm.contig"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX))
       #try using contigs instead of contigs extracted from scaffolds
       run_process(_settings, "cp %s/Assemble/out/%s.asm.contig  %s/FindORFS/in/%s.asm.contig"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
   else:

       run_process(_settings, "unlink %s/FindORFS/in/%s.asm.contig"%(_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings, "ln -t %s/FindORFS/in/ -s %s/Assemble/out/%s.asm.contig"%(_settings.rundir,_settings.rundir,_settings.PREFIX),"FindORFS")


   #run_process(_settings, "ln -t %s/FindORFS/in/ -s %s/Assemble/out/%s.asm.scafSeq.contigs"%(_settings.rundir,_settings.rundir,_settings.PREFIX))
   if _orf == "metagenemark":
       run_process(_settings, "%s/gmhmmp -o %s/FindORFS/out/%s.orfs -m %s/config/MetaGeneMark_v1.mod -d -a %s/FindORFS/in/%s.asm.contig"%(_settings.GMHMMP,_settings.rundir,_settings.PREFIX,_settings.METAMOS_UTILS,_settings.rundir,_settings.PREFIX),"FindORFS")
       parse_genemarkout("%s/FindORFS/out/%s.orfs"%(_settings.rundir,_settings.PREFIX))
       run_process(_settings, "unlink %s/Annotate/in/%s.faa"%(_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings, "unlink %s/Annotate/in/%s.fna"%(_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings, "unlink %s/FindRepeats/in/%s.fna"%(_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings, "ln -t %s/Annotate/in/ -s %s/FindORFS/out/%s.faa"%(_settings.rundir,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings, "ln -t %s/FindRepeats/in/ -s %s/FindORFS/out/%s.fna"%(_settings.rundir,_settings.rundir,_settings.PREFIX),"FindORFS")
   elif _orf == "fraggenescan":
       run_process(_settings,"%s/FragGeneScan -s %s/FindORFS/in/%s.asm.contig -o %s/FindORFS/out/%s.orfs -w 0 -t complete"%(_settings.FRAGGENESCAN,_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX))
       parse_fraggenescanout("%s/FindORFS/out/%s.orfs"%(_settings.rundir,_settings.PREFIX))
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.ffn %s/FindORFS/out/%s.fna"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.faa %s/FindORFS/out/%s.faa"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.ffn %s/Annotate/in/%s.fna"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.faa %s/Annotate/in/%s.faa"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.ffn %s/FindRepeats/in/%s.fna"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
       run_process(_settings,"cp %s/FindORFS/out/%s.orfs.faa %s/FindRepeats/in/%s.faa"%(_settings.rundir,_settings.PREFIX,_settings.rundir,_settings.PREFIX),"FindORFS")
   else:
       #not recognized
       return 1