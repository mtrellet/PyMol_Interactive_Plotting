import argparse
import os
import logging

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local",
        help="The visualisation mode (local or moliscope)")

    args = parser.parse_args()
    logging.info(args.mode)
    os.popen("pymol -r 3d_handler_pymol.py -- %s" % args.mode)
