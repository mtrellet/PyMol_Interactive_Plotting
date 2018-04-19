from sys import argv
from pymol import cmd

print sys.argv

name = os.path.basename(os.path.splitext(sys.argv[2])[0])

cmd.load(sys.argv[2])
cmd.do('split_states %s, prefix=""' % name)

cmd.do("delete %s" % name)

cmd.do("hide everything")

set cartoon_transparency, 0.1
set stick_radius, 0.40

disable sele