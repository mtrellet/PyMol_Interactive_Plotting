import argparse
import os
import logging

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local",
        help="The visualisation mode (local or moliscope)")

    parser.add_argument("--pdb",
        help="PDB file path with models to be loaded (ex: ~/Dev/Molecules_data/00_PEPTIDE.200/trajectory/pdbs/peptide_fit.pdb)")

    args = parser.parse_args()
    print args.mode
    print args.pdb
    os.popen("/programs/i386-mac/pymol/2.0.6/PyMOL.app/Contents/bin/pymol ../load_traj.pml -r 3d_handler_pymol.py -- {} {}".format(args.mode, args.pdb))
