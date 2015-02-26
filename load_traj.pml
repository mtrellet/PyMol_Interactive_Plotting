
load ~/Dev/Molecules_data/00_PEPTIDE.200/trajectory/pdbs/peptide_fit_200_207.pdb

split_states peptide_fit, prefix=""

set_name 0001, 0201
set_name 0002, 0202
set_name 0003, 0203
set_name 0004, 0204
set_name 0005, 0205
set_name 0006, 0206
set_name 0007, 0207

delete peptide_fit_200_207

hide everything

disable sele